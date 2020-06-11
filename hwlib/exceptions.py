


class BlockInstFuncException(Exception):

  def __init__(self,obj,func,blk,loc,text):
    msg = "[%s.%s] %s(%s) : %s" % (obj.__class__.__name__, \
                                   func,blk,loc,text)
    Exception.__init__(self,msg)
