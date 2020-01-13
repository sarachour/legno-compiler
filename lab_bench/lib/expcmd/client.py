from lab_bench.lib.base_command import Command

class WaitForKeypress(Command):


  def __init__(self):
    Command.__init__(self)

  @staticmethod
  def name():
    return "wait_for_key"

  @staticmethod
  def desc():
    return "[client] wait for keypress"

  def __repr__(self):
    return self.name()


  @staticmethod
  def parse(args):
    return WaitForKeypress()

  def execute(self,state):
    input("press any key to continue")
