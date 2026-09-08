/**
 * TRACE — Master Settings, Dynamic Roles & Menu Permissions Management Page
 */
import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import {
  Shield, Briefcase, Building2, Clock, Plus, Trash2, Check, X, RefreshCw, Lock, LayoutGrid, Layers
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { masterApi, employeesApi, hrmsApi } from '@/api'

export default function MasterPage() {
  const [designations, setDesignations] = useState([])
  const [departments, setDepartments] = useState([])
  const [shifts, setShifts] = useState([])
  const [roles, setRoles] = useState([])
  const [menus, setMenus] = useState([])
  const [permissionMatrix, setPermissionMatrix] = useState([])
  const [loading, setLoading] = useState(true)

  // Dialog states
  const [showDesigModal, setShowDesigModal] = useState(false)
  const [desigForm, setDesigForm] = useState({ name: '', description: '' })

  const [showRoleModal, setShowRoleModal] = useState(false)
  const [roleForm, setRoleForm] = useState({ role_name: '' })

  const [showMenuModal, setShowMenuModal] = useState(false)
  const [menuForm, setMenuForm] = useState({ key: '', label: '', icon: 'LayoutDashboard' })

  const [showDeptModal, setShowDeptModal] = useState(false)
  const [deptForm, setDeptForm] = useState({ name: '', description: '' })

  const [showShiftModal, setShowShiftModal] = useState(false)
  const [shiftForm, setShiftForm] = useState({ schedule_name: '', start_time: '09:00', end_time: '18:00', break_minutes: 60 })

  const fetchData = async () => {
    setLoading(true)
    try {
      const [desigRes, deptRes, shiftsRes, rolesRes, menusRes, matrixRes] = await Promise.all([
        masterApi.getDesignations().catch(() => ({ data: [] })),
        employeesApi.listDepartments().catch(() => ({ data: [] })),
        hrmsApi.getShifts().catch(() => ({ data: [] })),
        masterApi.getRoles().catch(() => ({ data: { roles: [] } })),
        masterApi.getMenus().catch(() => ({ data: { menus: [] } })),
        masterApi.getMenuPermissions().catch(() => ({ data: { matrix: [] } })),
      ])
      setDesignations(desigRes.data || [])
      setDepartments(deptRes.data || [])
      setShifts(shiftsRes.data || [])
      setRoles(rolesRes.data?.roles || [])
      setMenus(menusRes.data?.menus || [])
      setPermissionMatrix(matrixRes.data?.matrix || [])
    } catch (err) {
      toast.error('Failed to load master settings data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Designation handlers
  const handleAddDesignation = async (e) => {
    e.preventDefault()
    if (!desigForm.name) return
    try {
      await masterApi.createDesignation(desigForm)
      toast.success(`Designation '${desigForm.name}' created successfully`)
      setShowDesigModal(false)
      setDesigForm({ name: '', description: '' })
      fetchData()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create designation')
    }
  }

  const handleDeleteDesignation = async (id) => {
    if (!confirm('Delete this designation?')) return
    try {
      await masterApi.deleteDesignation(id)
      toast.success('Designation deleted')
      fetchData()
    } catch (err) {
      toast.error('Failed to delete designation')
    }
  }

  // Dynamic Role Handlers
  const handleAddRole = async (e) => {
    e.preventDefault()
    if (!roleForm.role_name) return
    try {
      await masterApi.createRole(roleForm)
      toast.success(`System Role '${roleForm.role_name}' created successfully`)
      setShowRoleModal(false)
      setRoleForm({ role_name: '' })
      fetchData()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create role')
    }
  }

  const handleDeleteRole = async (roleObj) => {
    if (!confirm(`Delete custom role '${roleObj.role_name}'?`)) return
    try {
      await masterApi.deleteRole(roleObj.id)
      toast.success('Role deleted')
      fetchData()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete role')
    }
  }

  // Dynamic Navigation Menu Handlers
  const handleAddMenu = async (e) => {
    e.preventDefault()
    if (!menuForm.label || !menuForm.key) return
    try {
      await masterApi.createMenu(menuForm)
      toast.success(`Navigation menu '${menuForm.label}' created`)
      setShowMenuModal(false)
      setMenuForm({ key: '', label: '', icon: 'LayoutDashboard' })
      fetchData()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create menu')
    }
  }

  const handleDeleteMenu = async (menuObj) => {
    if (!confirm(`Delete custom menu '${menuObj.label}'?`)) return
    try {
      await masterApi.deleteMenu(menuObj.id)
      toast.success('Menu module deleted')
      fetchData()
    } catch (err) {
      toast.error('Failed to delete menu')
    }
  }

  // Department handlers
  const handleAddDepartment = async (e) => {
    e.preventDefault()
    if (!deptForm.name) return
    try {
      await employeesApi.createDepartment(deptForm)
      toast.success(`Department '${deptForm.name}' created`)
      setShowDeptModal(false)
      setDeptForm({ name: '', description: '' })
      fetchData()
    } catch (err) {
      toast.error('Failed to create department')
    }
  }

  // Shift handlers
  const handleAddShift = async (e) => {
    e.preventDefault()
    if (!shiftForm.schedule_name) return
    try {
      await hrmsApi.createShift(shiftForm)
      toast.success(`Shift '${shiftForm.schedule_name}' created`)
      setShowShiftModal(false)
      setShiftForm({ schedule_name: '', start_time: '09:00', end_time: '18:00', break_minutes: 60 })
      fetchData()
    } catch (err) {
      toast.error('Failed to create shift')
    }
  }

  // Menu Permission toggle handler
  const handleTogglePermission = async (roleName, menuKey, currentAllowed) => {
    const updated = permissionMatrix.map(roleObj => {
      if (roleObj.role_name === roleName) {
        return {
          ...roleObj,
          permissions: roleObj.permissions.map(p =>
            p.menu_key === menuKey ? { ...p, is_allowed: !currentAllowed } : p
          )
        }
      }
      return roleObj
    })
    setPermissionMatrix(updated)

    try {
      await masterApi.updateMenuPermissions([{ role_name: roleName, menu_key: menuKey, is_allowed: !currentAllowed }])
      toast.success(`Updated ${menuKey} access for ${roleName}`)
    } catch (err) {
      toast.error('Failed to update permission')
      fetchData()
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-[1400px]">
      <div className="flex justify-between items-center flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Master & Access Control</h1>
          <p className="text-sm text-muted-foreground">Manage dynamic system roles, job designations, modules, and menu access permissions</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData}><RefreshCw className="size-4 mr-1" />Refresh</Button>
      </div>

      <Tabs defaultValue="designations">
        <TabsList className="flex-wrap">
          <TabsTrigger value="designations"><Briefcase className="size-4 mr-1" />Designations ({designations.length})</TabsTrigger>
          <TabsTrigger value="roles"><Shield className="size-4 mr-1" />System Roles ({roles.length})</TabsTrigger>
          <TabsTrigger value="permissions"><Lock className="size-4 mr-1" />Role-Menu Permissions</TabsTrigger>
          <TabsTrigger value="menus"><LayoutGrid className="size-4 mr-1" />Modules/Menus ({menus.length})</TabsTrigger>
          <TabsTrigger value="departments"><Building2 className="size-4 mr-1" />Departments ({departments.length})</TabsTrigger>
          <TabsTrigger value="shifts"><Clock className="size-4 mr-1" />Work Shifts ({shifts.length})</TabsTrigger>
        </TabsList>

        {/* DESIGNATIONS TAB */}
        <TabsContent value="designations" className="space-y-4 mt-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold text-lg">Job Designations Master</h3>
            <Button onClick={() => setShowDesigModal(true)}><Plus className="size-4 mr-1" />Add Designation</Button>
          </div>
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Designation Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {designations.map(d => (
                  <TableRow key={d.id}>
                    <TableCell className="font-medium text-sm">{d.name}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{d.description || 'N/A'}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteDesignation(d.id)}><Trash2 className="size-3 text-destructive" /></Button>
                    </TableCell>
                  </TableRow>
                ))}
                {designations.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center py-8 text-sm text-muted-foreground">
                      No designations added yet. Click 'Add Designation' above.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* DYNAMIC SYSTEM ROLES TAB */}
        <TabsContent value="roles" className="space-y-4 mt-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="font-semibold text-lg">System Roles Master</h3>
              <p className="text-xs text-muted-foreground">Define roles available across user registration, employee profiles, and access control</p>
            </div>
            <Button onClick={() => setShowRoleModal(true)}><Plus className="size-4 mr-1" />Add System Role</Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {roles.map(r => (
              <Card key={r.id || r.role_name}>
                <CardContent className="p-5 flex items-center justify-between">
                  <div className="space-y-1">
                    <Badge variant={['Admin', 'Manager'].includes(r.role_name) ? 'default' : 'secondary'}>
                      {r.role_name}
                    </Badge>
                    <div className="text-xs text-muted-foreground">{['Admin', 'Manager', 'Employee'].includes(r.role_name) ? 'Built-in System Role' : 'Custom Dynamic Role'}</div>
                  </div>
                  {!['Admin', 'Manager', 'Employee'].includes(r.role_name) && r.id && (
                    <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteRole(r)}>
                      <Trash2 className="size-3.5 text-destructive" />
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* ROLE & MENU ACCESS MATRIX TAB */}
        <TabsContent value="permissions" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Lock className="size-4 text-primary" />
                Role-Based Sidebar Menu Permission Matrix
              </CardTitle>
              <CardDescription>
                Toggle which sidebar navigation modules are visible for each dynamic role in the system.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-48">Navigation Module</TableHead>
                      {permissionMatrix.map(r => (
                        <TableHead key={r.role_name} className="text-center font-bold">{r.role_name}</TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {permissionMatrix[0]?.permissions?.map(perm => (
                      <TableRow key={perm.menu_key}>
                        <TableCell className="font-medium text-xs capitalize">{perm.menu_label || perm.menu_key}</TableCell>
                        {permissionMatrix.map(roleObj => {
                          const p = roleObj.permissions.find(item => item.menu_key === perm.menu_key)
                          const allowed = p?.is_allowed
                          return (
                            <TableCell key={roleObj.role_name} className="text-center">
                              <Button
                                variant={allowed ? "default" : "outline"}
                                size="sm"
                                className="h-7 px-3 text-xs"
                                onClick={() => handleTogglePermission(roleObj.role_name, perm.menu_key, allowed)}
                              >
                                {allowed ? <Check className="size-3 mr-1" /> : <X className="size-3 mr-1 text-muted-foreground" />}
                                {allowed ? "Allowed" : "Hidden"}
                              </Button>
                            </TableCell>
                          )
                        })}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* NAVIGATION MENUS / MODULES TAB */}
        <TabsContent value="menus" className="space-y-4 mt-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="font-semibold text-lg">Navigation Menus & Modules</h3>
              <p className="text-xs text-muted-foreground">Manage navigation links available in the application</p>
            </div>
            <Button onClick={() => setShowMenuModal(true)}><Plus className="size-4 mr-1" />Add Menu Module</Button>
          </div>
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Menu Key</TableHead>
                  <TableHead>Display Label</TableHead>
                  <TableHead>Icon Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {menus.map(m => (
                  <TableRow key={m.key}>
                    <TableCell className="font-mono text-xs font-semibold">{m.key}</TableCell>
                    <TableCell className="text-sm font-medium">{m.label}</TableCell>
                    <TableCell className="text-xs font-mono text-muted-foreground">{m.icon || 'LayoutDashboard'}</TableCell>
                    <TableCell>
                      <Badge variant={m.is_custom ? "secondary" : "outline"}>{m.is_custom ? 'Custom' : 'System'}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {m.is_custom && m.id && (
                        <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteMenu(m)}>
                          <Trash2 className="size-3 text-destructive" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* DEPARTMENTS TAB */}
        <TabsContent value="departments" className="space-y-4 mt-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold text-lg">Departments</h3>
            <Button onClick={() => setShowDeptModal(true)}><Plus className="size-4 mr-1" />Add Department</Button>
          </div>
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Department Name</TableHead>
                  <TableHead>Description</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {departments.map(d => (
                  <TableRow key={d.id}>
                    <TableCell className="font-medium text-sm">{d.name}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{d.description || 'N/A'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* SHIFTS TAB */}
        <TabsContent value="shifts" className="space-y-4 mt-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold text-lg">Work Schedule Shifts</h3>
            <Button onClick={() => setShowShiftModal(true)}><Plus className="size-4 mr-1" />Add Shift</Button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {shifts.map(s => (
              <Card key={s.id}>
                <CardContent className="p-4 space-y-2">
                  <div className="font-semibold text-sm">{s.schedule_name}</div>
                  <div className="text-sm font-mono font-bold">{s.start_time} – {s.end_time}</div>
                  <div className="text-xs text-muted-foreground">Break: {s.break_minutes} mins</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Add Designation Dialog */}
      <Dialog open={showDesigModal} onOpenChange={setShowDesigModal}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add New Designation</DialogTitle></DialogHeader>
          <form onSubmit={handleAddDesignation} className="space-y-4">
            <div className="space-y-2">
              <Label>Designation Title *</Label>
              <Input placeholder="e.g. Senior Software Engineer" value={desigForm.name} onChange={e => setDesigForm({ ...desigForm, name: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input placeholder="Key responsibilities and role description" value={desigForm.description} onChange={e => setDesigForm({ ...desigForm, description: e.target.value })} />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowDesigModal(false)}>Cancel</Button>
              <Button type="submit">Save Designation</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Add System Role Dialog */}
      <Dialog open={showRoleModal} onOpenChange={setShowRoleModal}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add New System Role</DialogTitle></DialogHeader>
          <form onSubmit={handleAddRole} className="space-y-4">
            <div className="space-y-2">
              <Label>Role Name *</Label>
              <Input placeholder="e.g. QA Lead or HR Manager" value={roleForm.role_name} onChange={e => setRoleForm({ ...roleForm, role_name: e.target.value })} required />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowRoleModal(false)}>Cancel</Button>
              <Button type="submit">Save Role</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Add Menu Dialog */}
      <Dialog open={showMenuModal} onOpenChange={setShowMenuModal}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add Navigation Menu/Module</DialogTitle></DialogHeader>
          <form onSubmit={handleAddMenu} className="space-y-4">
            <div className="space-y-2">
              <Label>Menu Key (unique identifier) *</Label>
              <Input placeholder="e.g. analytics" value={menuForm.key} onChange={e => setMenuForm({ ...menuForm, key: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label>Display Label *</Label>
              <Input placeholder="e.g. Advanced Analytics" value={menuForm.label} onChange={e => setMenuForm({ ...menuForm, label: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label>Lucide Icon Name</Label>
              <Input placeholder="e.g. BarChart3 or FileText" value={menuForm.icon} onChange={e => setMenuForm({ ...menuForm, icon: e.target.value })} />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowMenuModal(false)}>Cancel</Button>
              <Button type="submit">Save Menu</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Add Department Dialog */}
      <Dialog open={showDeptModal} onOpenChange={setShowDeptModal}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add Department</DialogTitle></DialogHeader>
          <form onSubmit={handleAddDepartment} className="space-y-4">
            <div className="space-y-2">
              <Label>Department Name *</Label>
              <Input placeholder="e.g. Frontend Engineering" value={deptForm.name} onChange={e => setDeptForm({ ...deptForm, name: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input placeholder="Department description" value={deptForm.description} onChange={e => setDeptForm({ ...deptForm, description: e.target.value })} />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowDeptModal(false)}>Cancel</Button>
              <Button type="submit">Save Department</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Add Shift Dialog */}
      <Dialog open={showShiftModal} onOpenChange={setShowShiftModal}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add Shift Schedule</DialogTitle></DialogHeader>
          <form onSubmit={handleAddShift} className="space-y-4">
            <div className="space-y-2">
              <Label>Shift Name *</Label>
              <Input placeholder="e.g. Night Shift" value={shiftForm.schedule_name} onChange={e => setShiftForm({ ...shiftForm, schedule_name: e.target.value })} required />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Start Time *</Label><Input type="time" value={shiftForm.start_time} onChange={e => setShiftForm({ ...shiftForm, start_time: e.target.value })} required /></div>
              <div className="space-y-2"><Label>End Time *</Label><Input type="time" value={shiftForm.end_time} onChange={e => setShiftForm({ ...shiftForm, end_time: e.target.value })} required /></div>
            </div>
            <div className="space-y-2"><Label>Break (Minutes)</Label><Input type="number" value={shiftForm.break_minutes} onChange={e => setShiftForm({ ...shiftForm, break_minutes: Number(e.target.value) })} /></div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowShiftModal(false)}>Cancel</Button>
              <Button type="submit">Save Shift</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
