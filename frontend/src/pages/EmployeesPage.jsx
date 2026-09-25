/**
 * TRACE — Employees Page
 * Full CRUD connected to /employees, /departments, and /designations APIs.
 * Supports direct creation of user login credentials (Email, Password, Role) during employee addition.
 */

import { useState, useEffect, useMemo } from 'react'
import { Users, Search, Plus, RefreshCw, CheckCircle, AlertTriangle, X, Pencil, Trash2, Mail, Shield, Briefcase } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { employeesApi } from '@/api'
import { toast } from 'sonner'

const STATUS_BADGE = {
  Active: 'default',
  'On Leave': 'secondary',
  Inactive: 'destructive',
  Probation: 'outline',
}

export default function EmployeesPage() {
  const [employees, setEmployees] = useState([])
  const [departments, setDepartments] = useState([])
  const [designations, setDesignations] = useState([])
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [deptFilter, setDeptFilter] = useState('All')
  const [total, setTotal] = useState(0)

  const [showModal, setShowModal] = useState(false)
  const [editingEmployee, setEditingEmployee] = useState(null)
  const [empForm, setEmpForm] = useState({
    name: '',
    email: '',
    password: '',
    role: 'Employee',
    employee_code: '',
    department_id: '',
    designation_id: '',
    status: 'Active',
    joining_date: '',
  })
  const [saving, setSaving] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [empRes, deptRes, desigRes] = await Promise.all([
        employeesApi.list({ per_page: 100 }).catch(() => ({ data: { employees: [], total: 0 } })),
        employeesApi.listDepartments().catch(() => ({ data: [] })),
        employeesApi.getDesignations().catch(() => ({ data: [] })),
      ])
      setEmployees(empRes.data.employees || [])
      setTotal(empRes.data.total || 0)
      setDepartments(deptRes.data || [])
      setDesignations(desigRes.data || [])
      setRoles([{ role_name: 'Admin' }, { role_name: 'Manager' }, { role_name: 'Employee' }])
    } catch (err) {
      toast.error('Failed to load employees')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const departmentNames = ['All', ...departments.map((d) => d.name)]

  const filtered = useMemo(() => {
    return employees.filter((emp) => {
      const empName = emp.user?.name || emp.employee_code || ''
      const empEmail = emp.user?.email || ''
      const deptName = emp.department?.name || ''
      const desigName = emp.designation?.name || ''
      const matchesSearch =
        empName.toLowerCase().includes(search.toLowerCase()) ||
        empEmail.toLowerCase().includes(search.toLowerCase()) ||
        deptName.toLowerCase().includes(search.toLowerCase()) ||
        desigName.toLowerCase().includes(search.toLowerCase()) ||
        emp.employee_code.toLowerCase().includes(search.toLowerCase())
      const matchesDept = deptFilter === 'All' || deptName === deptFilter
      return matchesSearch && matchesDept
    })
  }, [search, deptFilter, employees])

  const handleSaveEmployee = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editingEmployee) {
        await employeesApi.update(editingEmployee.id, {
          employee_code: empForm.employee_code,
          department_id: empForm.department_id && empForm.department_id !== 'none' ? Number(empForm.department_id) : null,
          designation_id: empForm.designation_id && empForm.designation_id !== 'none' ? Number(empForm.designation_id) : null,
          status: empForm.status,
          joining_date: empForm.joining_date || null,
        })
        toast.success('Employee updated successfully!')
      } else {
        await employeesApi.create({
          name: empForm.name,
          email: empForm.email,
          password: empForm.password,
          role: empForm.role,
          employee_code: empForm.employee_code,
          department_id: empForm.department_id && empForm.department_id !== 'none' ? Number(empForm.department_id) : null,
          designation_id: empForm.designation_id && empForm.designation_id !== 'none' ? Number(empForm.designation_id) : null,
          status: empForm.status,
          joining_date: empForm.joining_date || null,
        })
        toast.success(`Employee ${empForm.name || empForm.employee_code} created with login credentials!`)
      }
      setShowModal(false)
      setEditingEmployee(null)
      fetchData()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save employee')
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteEmployee = async (id) => {
    if (!confirm('Are you sure you want to deactivate this employee?')) return
    try {
      await employeesApi.delete(id)
      toast.success('Employee deactivated successfully')
      fetchData()
    } catch {
      toast.error('Failed to deactivate employee')
    }
  }

  const openAdd = () => {
    setEditingEmployee(null)
    setEmpForm({
      name: '',
      email: '',
      password: '',
      role: 'Employee',
      employee_code: `TRACE-${Math.floor(100 + Math.random() * 900)}`,
      department_id: departments[0]?.id ? String(departments[0].id) : 'none',
      designation_id: designations[0]?.id ? String(designations[0].id) : 'none',
      status: 'Active',
      joining_date: new Date().toISOString().split('T')[0],
    })
    setShowModal(true)
  }

  const openEdit = (emp) => {
    setEditingEmployee(emp)
    setEmpForm({
      name: emp.user?.name || '',
      email: emp.user?.email || '',
      password: '',
      role: emp.user?.role || 'Employee',
      employee_code: emp.employee_code,
      department_id: emp.department_id ? String(emp.department_id) : 'none',
      designation_id: emp.designation_id ? String(emp.designation_id) : 'none',
      status: emp.status,
      joining_date: emp.joining_date || '',
    })
    setShowModal(true)
  }

  return (
    <div id="employees-page" className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Employees Directory</h1>
          <p className="text-sm text-muted-foreground">{total} team members across departments & designations</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={fetchData} title="Refresh">
            <RefreshCw className="size-4" />
          </Button>
          <Button onClick={openAdd}>
            <Plus className="size-4 mr-1" /> Add Employee
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4 flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search by name, email, code, designation…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {departmentNames.map((dept) => (
              <Button
                key={dept}
                variant={deptFilter === dept ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDeptFilter(dept)}
              >
                {dept}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Employee</TableHead>
              <TableHead>Code</TableHead>
              <TableHead>Designation</TableHead>
              <TableHead className="hidden md:table-cell">Department</TableHead>
              <TableHead>System Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((emp) => {
              const uName = emp.user?.name || `Employee #${emp.user_id}`
              const uEmail = emp.user?.email || '—'
              const initials = uName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
              return (
                <TableRow key={emp.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar className="size-8">
                        <AvatarFallback className="text-xs bg-primary/10 text-primary font-bold">{initials}</AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="text-xs font-semibold">{uName}</div>
                        <div className="text-[11px] text-muted-foreground flex items-center gap-1">
                          <Mail className="size-3" /> {uEmail}
                        </div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-xs font-medium">{emp.employee_code}</TableCell>
                  <TableCell className="text-xs">
                    <Badge variant="outline" className="font-normal text-xs">{emp.designation?.name || 'Unassigned'}</Badge>
                  </TableCell>
                  <TableCell className="text-xs hidden md:table-cell">
                    {emp.department?.name || '—'}
                  </TableCell>
                  <TableCell className="text-xs">
                    <Badge variant="secondary" className="text-[10px]"><Shield className="size-2.5 mr-1" />{emp.user?.role || 'Employee'}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={STATUS_BADGE[emp.status] || 'secondary'}>{emp.status}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => openEdit(emp)}>
                        <Pencil className="size-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteEmployee(emp.id)}>
                        <Trash2 className="size-3.5 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              )
            })}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-10 text-sm text-muted-foreground">
                  No employees found. Click 'Add Employee' to create one.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Employee Modal */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingEmployee ? `Edit Employee (${editingEmployee.employee_code})` : 'Create Employee with Login Credentials'}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSaveEmployee} className="space-y-4">
            {!editingEmployee && (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="emp-name">Full Name *</Label>
                    <Input
                      id="emp-name"
                      type="text"
                      value={empForm.name}
                      onChange={(e) => setEmpForm({ ...empForm, name: e.target.value })}
                      required
                      placeholder="e.g. Jane Doe"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="emp-email">Email Address *</Label>
                    <Input
                      id="emp-email"
                      type="email"
                      value={empForm.email}
                      onChange={(e) => setEmpForm({ ...empForm, email: e.target.value })}
                      required
                      placeholder="jane@trace.internal"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="emp-password">Login Password *</Label>
                    <Input
                      id="emp-password"
                      type="password"
                      value={empForm.password}
                      onChange={(e) => setEmpForm({ ...empForm, password: e.target.value })}
                      required
                      placeholder="••••••••"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>System Role *</Label>
                    <Select
                      value={empForm.role}
                      onValueChange={(v) => setEmpForm({ ...empForm, role: v })}
                    >
                      <SelectTrigger><SelectValue placeholder="Select Role" /></SelectTrigger>
                      <SelectContent>
                        {roles.map(r => (
                          <SelectItem key={r.role_name} value={r.role_name}>{r.role_name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="emp-code">Employee Code *</Label>
                <Input
                  id="emp-code"
                  type="text"
                  value={empForm.employee_code}
                  onChange={(e) => setEmpForm({ ...empForm, employee_code: e.target.value })}
                  required
                  placeholder="TRACE-001"
                />
              </div>
              <div className="space-y-2">
                <Label>Designation</Label>
                <Select
                  value={String(empForm.designation_id || 'none')}
                  onValueChange={(v) => setEmpForm({ ...empForm, designation_id: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Designation" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {designations.map((d) => (
                      <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Department</Label>
                <Select
                  value={String(empForm.department_id || 'none')}
                  onValueChange={(v) => setEmpForm({ ...empForm, department_id: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Department" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {departments.map((d) => (
                      <SelectItem key={d.id} value={String(d.id)}>{d.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Status</Label>
                <Select
                  value={empForm.status}
                  onValueChange={(v) => setEmpForm({ ...empForm, status: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Active">Active</SelectItem>
                    <SelectItem value="On Leave">On Leave</SelectItem>
                    <SelectItem value="Probation">Probation</SelectItem>
                    <SelectItem value="Inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="emp-joining">Joining Date</Label>
              <Input
                id="emp-joining"
                type="date"
                value={empForm.joining_date}
                onChange={(e) => setEmpForm({ ...empForm, joining_date: e.target.value })}
              />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowModal(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : editingEmployee ? 'Update Employee' : 'Create Employee & Account'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
