import ops.op as op
from enum import Enum
import re
#from pyparsing import *
#import operator
import math
import lark

GRAMMAR = '''
?start: sum
    ?sum: product
        | sum "+" product   -> add
        | sum "-" product   -> sub
    ?product: atom
        | product "*" atom  -> mul
        | product "/" atom  -> div
    ?args: atom
         | args "," atom -> lst
    ?atom: NUMBER           -> number
         | "-" atom         -> neg
         | atom "^" atom -> pow
         | NAME             -> var
         | NAME "(" args ")"      -> func
         | "(" sum ")"
    %import common.CNAME -> NAME
    %import common.NUMBER
    %import common.WS_INLINE
    %ignore WS_INLINE
'''

PARSER = lark.Lark(GRAMMAR)

def report(clause,msg):
  if not clause:
    raise Exception("when parsing : %s" % (msg))

def function_to_dslang_ast(dsprog,name,arguments,ignore_missing_func=False):
  print(arguments)
  n = len(arguments)
  if not dsprog is None and dsprog.has_lambda(name):
    freevars,impl = dsprog.lambda_spec(name);
    report(len(freevars) == n, \
           "expected <%d> args, got <%d>" % (len(freevars),n))
    return op.Call(arguments, \
                   op.Func(freevars, impl));
  elif name == "sin":
    report(n == 1, "expected 1 argument to sin function")
    return op.Sin(arguments[0])
  elif name == "sgn":
    report(n == 1, "expected 1 argument to sgn function")
    return op.Sgn(arguments[0])
  elif name == "sqrt":
    report(n == 1, "expected 1 argument to sqrt function")
    return op.Sqrt(arguments[0])
  elif name == "abs":
    report(n == 1, "expected 1 argument to abs function")
    return op.Abs(arguments[0])
  elif name == "max":
    report(n == 2, "expected 2 arguments to max function")
    return op.Max(arguments[0],arguments[1])
  elif name == "min":
    report(n == 2, "expected 2 arguments to min function")
    return op.Min(arguments[0],arguments[1])

  elif ignore_missing_func:
    raise Exception("unknown built-in function <%s>" % name)
  else:
    args = list(map(lambda i: "x%d" % i, range(n)))
    return op.Call(arguments, op.Func(args,None))

def lark_to_dslang_ast(dsprog,node):
  def recurse(ch):
    return lark_to_dslang_ast(dsprog,ch)

  n = len(node.children)
  if node.data == "neg":
    report(n == 1, "negation operation takes one argument");
    expr = recurse(node.children[0])
    if(expr.op == op.OpType.CONST):
        return op.Const(-1*expr.value);
    else:
        return op.Mult(op.Const(-1),expr)

  if node.data == "func":
    report(n > 0, "function name not specified");
    func_name = node.children[0]
    report(func_name.type == "NAME", "expected Token.NAME");
    arguments = recurse(node.children[1])
    if not isinstance(arguments,list):
      arguments = [arguments]
    return function_to_dslang_ast(dsprog,func_name.value,arguments);

  if node.data == "number":
    number = node.children[0]
    report(number.type == "NUMBER", "expected Token.NUMBER");
    value = float(number.value)
    return op.Const(value)

  if node.data == "var":
    report(n == 1, "variable must have token");
    var_name = node.children[0]
    report(var_name.type == "NAME", "expected Token.NAME");
    return op.Var(var_name.value)

  if node.data == "sub":
    report(n == 2, "only binary subtraction are supported");
    e1 = recurse(node.children[0])
    e2 = recurse(node.children[1])
    return op.Add(e1,op.Mult(op.Const(-1),e2))


  if node.data == "add":
    report(n == 2, "only binary adds are supported");
    e1 = recurse(node.children[0])
    e2 = recurse(node.children[1])
    return op.Add(e1,e2)

  if node.data == "mul":
    report(n == 2, "only binary mults are supported");
    e1 = recurse(node.children[0])
    e2 = recurse(node.children[1])
    return op.Mult(e1,e2)

  if node.data == "div":
    report(n == 2, "only binary div are supported");
    e1 = recurse(node.children[0])
    e2 = recurse(node.children[1])
    return op.Div(e1,e2)

  if node.data == "pow":
    report(n == 2, "only binary div are supported");
    e1 = recurse(node.children[0])
    e2 = recurse(node.children[1])
    return op.Pow(e1,e2)


  if node.data == "lst":
    e1 = recurse(node.children[0])
    e2 = recurse(node.children[1])
    if not isinstance(e1,list):
      e1 = [e1]
    e1.append(e2)
    return e1

  else:
    raise Exception("unknown operator: %s" % node.data);


def parse(dsprog,strrepr):
  lark_ast = PARSER.parse(strrepr)
  obj = lark_to_dslang_ast(dsprog,lark_ast)
  return obj

def parse_expr(strrepr):
  lark_ast = PARSER.parse(strrepr)
  obj = lark_to_dslang_ast(None,lark_ast)
  return obj
