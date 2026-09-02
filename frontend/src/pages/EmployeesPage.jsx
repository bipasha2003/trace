/**
 * TRACE — Employees Page
 * Connected to /employees and /departments APIs with Add, Edit, Delete, and Search capabilities.
 */

import { useState, useEffect, useMemo } from 'react'
import { Users, Search, Plus, RefreshCw, CheckCircle, AlertTriangle, X, Pencil, Trash2 } from 'lucide-react'
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

const STATUS_BADGE = {
  Active: 'default',
  'On Leave': 'secondary',
  Inactive: 'destructive',
  Probation: 'outline',
}

export default function EmployeesPage() {
  const [employees, setEmployees] = useState([])
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [deptFilter, setDeptFilter] = useState('All')
  const [total, setTotal] = useState(0)

  const [showModal, setShowModal] = useState(false)
  const [actionMsg, setActionMsg] = useState(null)
  const [editingEmployee, setEditingEmployee] = useState(null)
  const [empForm, setEmpForm] = useState({
    user_id: '', employee_code: '', department_id: '', status: 'Active', joining_date: '',
  })
  const [saving, setSaving] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [empRes, deptRes] = await Promise.all([
        employeesApi.list({ per_page: 100 }),
        employeesApi.listDepartments(),
      ])
      setEmployees(empRes.data.employees || [])
      setTotal(empRes.data.total || 0)
      setDepartments(deptRes.data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load employees')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const departmentNames = ['All', ...departments.map((d) => d.name)]

  const filtered = useMemo(() => {
    return employees.filter((emp) => {
      const empName = emp.employee_code || ''
      const deptName = emp.department?.name || ''
      const matchesSearch =
        empName.toLowerCase().includes(search.toLowerCase()) ||
        deptName.toLowerCase().includes(search.toLowerCase()) ||
        String(emp.user_id).includes(search)
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
          department_id: empForm.department_id ? Number(empForm.department_id) : null,
          status: empForm.status,
          joining_date: empForm.joining_date || null,
        })
        setActionMsg({ type: 'success', text: 'Employee updated successfully!' })
      } else {
        await employeesApi.create({
          user_id: Number(empForm.user_id),
          employee_code: empForm.employee_code,
          department_id: empForm.department_id ? Number(empForm.department_id) : null,
          status: empForm.status,
          joining_date: empForm.joining_date || null,
        })
        setActionMsg({ type: 'success', text: 'Employee added successfully!' })
      }
      setShowModal(false)
      setEditingEmployee(null)
      setEmpForm({ user_id: '', employee_code: '', department_id: '', status: 'Active', joining_date: '' })
      fetchData()
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to save employee' })
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteEmployee = async (id) => {
    if (!confirm('Are you sure you want to delete this employee?')) return
    try {
      await employeesApi.delete(id)
      setActionMsg({ type: 'success', text: 'Employee deleted successfully' })
      fetchData()
    } catch {
      setActionMsg({ type: 'error', text: 'Failed to delete employee' })
    }
  }

  const openAdd = () => {
    setEditingEmployee(null)
    setEmpForm({
      user_id: '1',
      employee_code: `TRACE-${Math.floor(100 + Math.random() * 900)}`,
      department_id: departments[0]?.id || '',
      status: 'Active',
      joining_date: new Date().toISOString().split('T')[0],
    })
    setShowModal(true)
  }

  const openEdit = (emp) => {
    setEditingEmployee(emp)
    setEmpForm({
      user_id: emp.user_id,
      employee_code: emp.employee_code,
      department_id: emp.department_id || '',
      status: emp.status,
      joining_date: emp.joining_date || '',
    })
    setShowModal(true)
  }

  return (
    <div id="employees-page" className="space-y-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Employees Directory</h1>
          <p className="text-sm text-muted-foreground">{total} team members</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={fetchData} title="Refresh">
            <RefreshCw className="size-4" />
          </Button>
          <Button onClick={openAdd}>
            <Plus className="size-4" /> Add Employee
          </Button>
        </div>
      </div>

      {/* Messages */}
      {actionMsg && (
        <Alert variant={actionMsg.type === 'success' ? 'default' : 'destructive'}>
          {actionMsg.type === 'success'
            ? <CheckCircle className="size-4" />
            : <AlertTriangle className="size-4" />}
          <AlertDescription className="flex items-center justify-between">
            {actionMsg.text}
            <button onClick={() => setActionMsg(null)} className="ml-4">
              <X className="size-4" />
            </button>
          </AlertDescription>
        </Alert>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="p-4 flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search by code, ID or department…"
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
              <TableHead className="hidden md:table-cell">Department</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="hidden lg:table-cell">Join Date</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((emp) => (
              <TableRow key={emp.id}>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <Avatar className="size-8">
                      <AvatarFallback className="text-xs">E{emp.user_id}</AvatarFallback>
                    </Avatar>
                    <div>
                      <div className="text-xs font-medium">Employee #{emp.user_id}</div>
                      <div className="text-xs text-muted-foreground">ID: {emp.id}</div>
                    </div>
                  </div>
                </TableCell>
                <TableCell className="font-mono text-xs">{emp.employee_code}</TableCell>
                <TableCell className="text-xs hidden md:table-cell">
                  {emp.department?.name || '—'}
                </TableCell>
                <TableCell>
                  <Badge variant={STATUS_BADGE[emp.status] || 'secondary'}>{emp.status}</Badge>
                </TableCell>
                <TableCell className="text-xs hidden lg:table-cell">
                  {emp.joining_date
                    ? new Date(emp.joining_date).toLocaleDateString('en-IN', {
                        day: 'numeric', month: 'short', year: 'numeric',
                      })
                    : '—'}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="icon-sm" onClick={() => openEdit(emp)}>
                      <Pencil className="size-3" />
                    </Button>
                    <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteEmployee(emp.id)}>
                      <Trash2 className="size-3" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-12 text-sm text-muted-foreground">
                  No employees found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Employee Modal */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingEmployee ? 'Edit Employee' : 'Add New Employee'}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSaveEmployee} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="emp-user-id">User ID *</Label>
                <Input
                  id="emp-user-id"
                  type="number"
                  value={empForm.user_id}
                  onChange={(e) => setEmpForm({ ...empForm, user_id: e.target.value })}
                  required
                  disabled={!!editingEmployee}
                  placeholder="1"
                />
              </div>
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
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Department</Label>
                <Select
                  value={String(empForm.department_id)}
                  onValueChange={(v) => setEmpForm({ ...empForm, department_id: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Department" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">None</SelectItem>
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
                {saving ? 'Saving…' : 'Save Employee'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
