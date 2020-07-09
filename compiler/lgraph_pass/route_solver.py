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

def ilp_and(ilp,clauses,name):
  total = len(clauses)
  tempvar_name = ilp_tempvar(ilp)
  tempvar = pulp.LpVariable(tempvar_name,
                            cat='Binary')
  ilp += (sum(clauses)-total*tempvar == 0),name
  return tempvar

def ilp_or(ilp,clauses,name):
  total = len(clauses)
  tempvar_name = ilp_tempvar(ilp)
  tempvar = pulp.LpVariable(tempvar_name,
                            cat='Binary')
  ilp += (total*tempvar-sum(clauses) <= total-1,name+".1")
  ilp += (total*tempvar-sum(clauses) >= 0,name+".2")
  return tempvar


def solve(prob):
  ilp = pulp.LpProblem("routing",pulp.LpMinimize)
  if not prob.valid:
    print("failed during problem construction: %s" % prob.message)
    return

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
  not_conn = ilp_not(ilp,conn_assign.ilpvar,name+".not")
  and_conn = ilp_and(ilp,[src_assign.ilpvar, \
                          dest_assign.ilpvar, \
                          conn_assign.ilpvar], \
                         name+".and")
  or_conn = ilp_or(ilp,[not_conn,and_conn],name+'.clause')
  ilp += or_conn == 1,name

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
    for ident_assign in prob.identifier_assigns:
      if ident_assign.ilpvar.varValue == 1.0:
        assigns.add(ident_assign)
    for conn_assign in prob.conn_assigns:
      if conn_assign.ilpvar.varValue == 1.0:
        assigns.add_conn(conn_assign)

    return assigns
  else:
    print("[WARN] Failed with status <%s>" % status)
    return None
