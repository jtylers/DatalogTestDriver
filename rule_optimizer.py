#!/usr/bin/env python3
import logging
import multiprocessing

import lexical_analyzer
from datalog_interpreter import DatalogInterpreter
from datalog_parser import DatalogProgram, Rules, Rule
from tokens import TokenError

logger = logging.getLogger(__name__)


class Vertex(Rule):
    def __init__(self, rule: Rule, index: int, rules: Rules):
        super().__init__(head=rule.head, predicates=rule.predicates)

        self.id = index
        self.edges = self.adjacency(rule, rules)
        self.reverse = self.reverse_edges(rule, rules)

    @staticmethod
    def adjacency(rule: Rule, rules: Rules) -> set:
        """
        For the given rule, calculate the rules that it affects
        """
        adjacent = set()
        for i, r in enumerate(rules.rules):
            if r.head.id in [p.id for p in rule.predicates]:
                adjacent.add(i)
                continue
        return adjacent

    @staticmethod
    def reverse_edges(rule: Rule, rules: Rules) -> set:
        """
        Calculate the reverse edges for this vertex
        """
        reverse = set()
        for i, r in enumerate(rules.rules):
            if rule.head.id in [p.id for p in r.predicates]:
                reverse.add(i)
                continue
        return reverse

    def __str__(self):
        return "R{}:{}".format(self.id, ",".join("R{}".format(r) for r in sorted(self.edges)))


class DependencyGraph:
    def __init__(self, rules: Rules):
        # TODO inherit from dict?
        self.rules = dict()

        # Each rule is assigned a unique ID
        for i, rule in enumerate(rules.rules):
            self.rules[i] = Vertex(rule, index=i, rules=rules)

        logger.debug("Reverse Forest:\n{}".format(self.reverse()))

    def reverse(self) -> str:
        """
        :return: A string representation of the reverse forest
        """
        return "\n".join(
            "R{}:{}".format(self.rules[i].id, ",".join("R{}".format(r) for r in sorted(self.rules[i].reverse)))
            for i in sorted(self.rules.keys())
        ) + "\n"

    def __str__(self):
        return "\n".join(str(self.rules[i]) for i in sorted(self.rules.keys())) + "\n"


class RuleOptimizer(DatalogInterpreter):
    def __init__(self, datalog_program: DatalogProgram):
        super().__init__(datalog_program, least_fix_point=False)

        # TODO Evaluate the rules in the order described by the rule optimizer
        self.dependency_graph = DependencyGraph(datalog_program.rules)
        self.rule_evaluation = self.evaluate_optimized_rules(order=self.dependency_graph)

        logger.info("Evaluating Queries")
        for query in datalog_program.queries.queries:
            self.rdbms[query] = self.evaluate_query(query)

    def evaluate_optimized_rules(self, order: DependencyGraph) -> str:
        return ""

    def __str__(self):
        result = "Dependency Graph\n{}\n".format(self.dependency_graph)
        result += "Rule Evaluation\n{}\n".format(self.rule_evaluation)

        manager = multiprocessing.Manager()
        results = manager.dict()
        jobs = []
        for i, query in enumerate(self.rdbms.keys()):
            p = multiprocessing.Process(target=self._str_worker, args=(i, query, results))
            jobs.append(p)
            p.start()
        for proc in jobs:
            proc.join()
        for i, _ in enumerate(self.rdbms.keys()):
            result += results[i]
        return result


if __name__ == "__main__":
    from argparse import ArgumentParser

    arg = ArgumentParser(description="Run the Rule Optimizer.  This consumes the previous labs.")
    arg.add_argument('-d', '--debug', help="The logging debug level to use", default=logging.NOTSET, metavar='LEVEL')
    arg.add_argument('file', help='datalog file to parse')
    args = arg.parse_args()

    logging.basicConfig(level=logging.ERROR)
    logger.setLevel(int(args.debug))

    logger.info("Detected {} CPUs".format(multiprocessing.cpu_count()))
    logger.debug("Parsing '%s'" % args.file)

    # Create class objects
    tokens = lexical_analyzer.scan(args.file)
    datalog = None
    try:
        datalog = DatalogProgram(tokens)
    except TokenError as t:
        print("Failure!\n  {}".format(t))
        exit(1)

    print(RuleOptimizer(datalog))
