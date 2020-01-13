from ops.aop import *

class Rule:

    def __init__(self,name):
        self.name = name

    def group_by(self,group_expr,exprs):
        grouped = {}
        for expr in exprs:
            group = group_expr(expr)
            if not group in grouped:
                grouped[group] = []

            grouped[group].append(expr)

        for group,matches in grouped.items():
            yield group,matches

    def generate_args(self,ast):
        raise NotImplementedError

    def apply_args(self,ast,args):
        raise NotImplementedError

    # test if this transformation is applicable
    def apply(self,ast):
        assert(isinstance(ast,AOp))
        for args in self.generate_args(ast):
            print("xform[%s]: %s" % (self.name,args))
            yield self.apply_args(ast,args)


class RNegateFanout(Rule):

    def __init__(self,board):
        Rule.__init__(self,"negate_fanout")
        coeffs = []
        block = board.block('fanout')
        for mode in block.comp_modes:
            for _,expr in block.dynamics(mode):
                coeffs.append(expr.coefficient())

        self._opts = set(coeffs)

    def vars_and_consts(self,terms):
        for term in terms:
            if term.op == AOpType.VAR:
                continue
            elif term.op == AOpType.CONST:
                continue
            else:
                return False
        return True

    def generate_args(self,ast):
        if ast.op == AOpType.CPROD and \
           ast.value in self._opts:
            if ast.input.op == AOpType.VAR:
                yield 1
            elif ast.input.op == AOpType.SUM:
                if self.vars_and_consts(ast.input.inputs):
                    yield 1

            elif ast.input.op == AOpType.VPROD:
                for idx,inp in enumerate(ast.input.inputs):
                    if inp.op == AOpType.VAR:
                        yield idx
                    elif inp.op == AOpType.SUM \
                         and self.vars_and_consts(inp.inputs):
                        yield idx

    def process_term(self,inp,coeff):
        if inp.op == AOpType.VAR:
            return AVar(inp.name,coeff)
        elif inp.op == AOpType.SUM:
            return ASum.make(list(map(lambda t: self.process_term(t,coeff), \
                                 inp.inputs)))
        else:
            raise Exception("unhandled process: <%s>" % inp)

    def apply_args(self,ast,term_idx):
        if ast.input.op == AOpType.VAR:
            return self.process_term(ast.input,ast.value)

        elif ast.input.op == AOpType.SUM:
            return self.process_term(ast.input,ast.value)

        elif ast.input.op == AOpType.VPROD:
            new_args = []
            for idx,inp in enumerate(ast.input.inputs):
                if idx == term_idx:
                    new_term = self.process_term(inp,ast.value)
                    new_args.append(new_term)
                else:
                    new_args.append(inp)

            return AProd.make(new_args)


        raise Exception("unhandled: %s" % ast)

def get_rules(board):
    rules = []
    rules.append(RNegateFanout(board))
    return rules
