import pulp
import compiler.lgraph_pass.route_problem as routelib

def groupby(keyfun,lst):
  groups = {}
  for el in lst:
    grps = keyfun(el)
    for grp in grps:
      if not str(grp) in groups:
        groups[str(grp)] = []
      groups[str(grp)].append(el)

  return groups.items()

def group_conn_assign_by_conn_identifier(lst):
  def keyfun(inst_assign):
    return ["((%s.%d.%s)->(%s.%d.%s))" % \
            (inst_assign.source_block.name,
             inst_assign.source_ident,
             inst_assign.source_port.name,
             inst_assign.dest_block.name,
             inst_assign.dest_ident,
             inst_assign.dest_port.name)]

  for key,value in groupby(keyfun,lst):
      yield key,value

def group_inst_assign_by_block_identifier(lst):
  def keyfun(inst_assign):
    return ["%s.%d" % (inst_assign.block.name,
                      inst_assign.ident)]

  for key,value in groupby(keyfun,lst):
      yield key,value

def group_assign_by_resource(lst):
  def keyfun(assign):
      return list(map(lambda res: str(res), \
                      assign.resources()))

  for key,value in groupby(keyfun,lst):
      yield key,value


def ilp_tempvar(ilp):
  return "temp%d" % len(ilp.variables())

def ilp_not(ilp,clause,name):
  return 1-clause

def ilp_implies(ilp,condvar,stmt,name):
  # condvar^stmt
  # if p then q
  # | p | q |
  # | 1 | 1 |
  # | 0 | 1 |
  # | 0 | 0 |
  # basically everything but
  # | 1 | 0 |
  ilp += (condvar <= stmt),name

def ilp_and(ilp,c1,c2,name):
  tempvar_name = ilp_tempvar(ilp)
  tempvar = pulp.LpVariable(tempvar_name,
                            cat='Binary')

  cstr = (c1+c2-2*tempvar >= 0)
  ilp += cstr,name+".lower"
  cstr = (c1+c2-2*tempvar <= 1)
  ilp += cstr,name+".upper"
  return tempvar


def solve(prob):
  ilp = pulp.LpProblem("routing",pulp.LpMinimize)
  if not prob.valid:
    print("failed during problem construction: %s" % prob.message)
    return None

  ident_assign_by_name = {}
  for ident_assign in prob.identifier_assigns:
    ident_assign.ilpvar = pulp.LpVariable(ident_assign,
                                          cat='Binary')
    ident_assign_by_name[str(ident_assign)] = ident_assign


  for conn_assign in prob.conn_assigns:
    conn_assign.ilpvar = pulp.LpVariable(conn_assign,
                                         cat='Binary')


  resource_by_name = {}
  for resource in prob.resources:
    resource.ilpvar = pulp.LpVariable(resource,
                                      lowBound=0,
                                      upBound=resource.limit(),
                                      cat='Integer')
    resource_by_name[str(resource)] = resource

  # objective function: minimize resource consumption
  ilp += sum(map(lambda r: r.ilpvar, prob.resources))

  # each identifier is assigned to exactly one instance
  for group_name,idents in \
      group_inst_assign_by_block_identifier(prob.identifier_assigns):
    ilp += sum(map(lambda ident: ident.ilpvar, idents)) == 1,group_name

  # each connection identifier is assigned to exactly one instance
  for group_name,idents in \
      group_conn_assign_by_conn_identifier(prob.conn_assigns):
    ilp += sum(map(lambda ident: ident.ilpvar, idents)) == 1,group_name

  # a connection assignment implies instance assignments
  for conn_assign in prob.conn_assigns:
    src_assign_key = routelib.BlockIdentifierAssignVar(conn_assign.dev, \
                                             conn_assign.source_block,
                                             conn_assign.source_ident,
                                             conn_assign.source_loc)
    dest_assign_key = routelib.BlockIdentifierAssignVar(conn_assign.dev, \
                                                conn_assign.dest_block,
                                              conn_assign.dest_ident,
                                                conn_assign.dest_loc)
    src_assign = ident_assign_by_name[str(src_assign_key)]
    dest_assign = ident_assign_by_name[str(dest_assign_key)]

    name = str(conn_assign)+":instances"
    and_conn = ilp_and(ilp, \
                       src_assign.ilpvar, \
                       dest_assign.ilpvar, \
                       name+".and")
    ilp_implies(ilp,conn_assign.ilpvar,and_conn,name+".implies")

  # each resource has a limited number quantity
  for resource_name,idents in \
      group_assign_by_resource(prob.identifier_assigns \
                                       + prob.conn_assigns):

      resource_var = resource_by_name[resource_name].ilpvar
      ilp += sum(map(lambda ident: ident.ilpvar, idents)) \
             == resource_var,resource_name



  ilp.solve()
  status = pulp.LpStatus[ilp.status]
  if status == "Optimal":
    assigns = routelib.LocAssignments()
    print("-- Instances ---")
    for ident_assign in prob.identifier_assigns:
      if ident_assign.ilpvar.varValue == 1.0:
        print(ident_assign)
        assigns.add(ident_assign)
    print("-- Connections ---")
    for conn_assign in prob.conn_assigns:
      if conn_assign.ilpvar.varValue == 1.0:
        print(conn_assign)
        print(conn_assign.path)
        assigns.add_conn(conn_assign)

    return assigns
  else:
    print("[WARN] Failed with status <%s>" % status)
    return None
