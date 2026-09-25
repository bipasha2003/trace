/**
 * TRACE — HRMS & Attendance Page
 * Manages daily clock-in/out, manager attendance overview, leaves, leave balances, holidays, shifts & bulk imports.
 */

import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import {
  Fingerprint, LogIn, LogOut, Upload, Plus, RefreshCw, Pencil, Trash2, Check, X, Clock, MapPin, Users, BarChart2, Calendar, ShieldCheck
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { attendanceApi, hrmsApi, employeesApi } from '@/api'
import { useAuth } from '@/contexts/AuthContext'

const LEAVE_STATUS_MAP = {
  Approved: 'default',
  Pending: 'secondary',
  Rejected: 'destructive',
}

export default function AttendancePage() {
  const { user } = useAuth()
  const [summary, setSummary] = useState({ total_employees: 0, present: 0, absent: 0, attendance_rate: 0 })
  const [records, setRecords] = useState([])
  const [allRecords, setAllRecords] = useState([])
  const [leaves, setLeaves] = useState([])
  const [leaveBalance, setLeaveBalance] = useState(null)
  const [holidays, setHolidays] = useState([])
  const [shifts, setShifts] = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [checkingIn, setCheckingIn] = useState(false)
  const [checkingOut, setCheckingOut] = useState(false)
  const [dateFilter, setDateFilter] = useState('')

  // Modals
  const [showLeaveModal, setShowLeaveModal] = useState(false)
  const [leaveForm, setLeaveForm] = useState({ leave_type: 'Casual', start_date: '', end_date: '', reason: '' })
  const [showHolidayModal, setShowHolidayModal] = useState(false)
  const [editingHoliday, setEditingHoliday] = useState(null)
  const [holidayForm, setHolidayForm] = useState({ name: '', holiday_date: '', type: 'Public', description: '' })
  const [showShiftModal, setShowShiftModal] = useState(false)
  const [editingShift, setEditingShift] = useState(null)
  const [shiftForm, setShiftForm] = useState({ schedule_name: '', start_time: '09:00', end_time: '18:00', break_minutes: 60 })
  const [showAssignShift, setShowAssignShift] = useState(false)
  const [assignShiftEmp, setAssignShiftEmp] = useState(null)
  const [assignShiftId, setAssignShiftId] = useState('')
  const [showBulkModal, setShowBulkModal] = useState(false)
  const [bulkEntity, setBulkEntity] = useState('holidays')
  const [bulkFile, setBulkFile] = useState(null)
  const [bulkLoading, setBulkLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [summaryRes, historyRes, allRes, leavesRes, balanceRes, holidaysRes, shiftsRes, empRes] = await Promise.all([
        attendanceApi.dailySummary().catch(() => ({ data: null })),
        attendanceApi.history({ per_page: 50 }).catch(() => ({ data: { records: [] } })),
        attendanceApi.allEmployees({ per_page: 50 }).catch(() => ({ data: { records: [] } })),
        hrmsApi.getLeaves().catch(() => ({ data: [] })),
        hrmsApi.getAllLeaveBalance().catch(() => ({ data: null })),
        hrmsApi.getHolidays().catch(() => ({ data: [] })),
        hrmsApi.getShifts().catch(() => ({ data: [] })),
        employeesApi.list({ per_page: 100 }).catch(() => ({ data: { employees: [] } })),
      ])

      setSummary(summaryRes?.data || { total_employees: 0, present: 0, absent: 0, attendance_rate: 0 })
      setRecords(Array.isArray(historyRes?.data?.records) ? historyRes.data.records : [])
      setAllRecords(Array.isArray(allRes?.data?.records) ? allRes.data.records : [])
      setLeaves(Array.isArray(leavesRes?.data) ? leavesRes.data : [])
      setLeaveBalance(balanceRes?.data || null)
      setHolidays(Array.isArray(holidaysRes?.data) ? holidaysRes.data : [])
      setShifts(Array.isArray(shiftsRes?.data) ? shiftsRes.data : [])
      setEmployees(Array.isArray(empRes?.data?.employees) ? empRes.data.employees : [])
    } catch (err) {
      toast.error('Failed to update attendance data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // NOTE: Employee clock-in/out removed — endpoint removed in Phase 0 cleanup.
  // AttendancePage is being rebuilt in Phase 2 (Admin workforce panel).
  const handleCheckIn = () => { toast.info('Clock-in is no longer available from this interface.') }
  const handleCheckOut = () => { toast.info('Clock-out is no longer available from this interface.') }

  const handleAssignShift = async (e) => {
    e.preventDefault()
    if (!assignShiftEmp || !assignShiftId) return
    try {
      await hrmsApi.assignShift(assignShiftEmp.id, Number(assignShiftId))
      toast.success(`Shift assigned to ${assignShiftEmp.employee_code}`)
      setShowAssignShift(false)
      fetchData()
    } catch (err) {
      toast.error('Failed to assign shift')
    }
  }

  const fmtTime = ts => {
    if (!ts) return '—'
    try {
      const d = new Date(typeof ts === 'string' && !ts.includes('T') ? ts.replace(' ', 'T') : ts)
      return isNaN(d.getTime()) ? String(ts) : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return String(ts)
    }
  }

  const fmtHours = h => {
    if (h == null || h === '') return '—'
    const n = Number(h)
    return isNaN(n) ? '—' : `${n.toFixed(2)}h`
  }

  const handleApplyLeave = async (e) => {
    e.preventDefault()
    try {
      await hrmsApi.createLeave({ employee_id: 1, ...leaveForm })
      toast.success('Leave request submitted successfully!')
      setShowLeaveModal(false)
      fetchData()
    } catch (err) {
      toast.error('Failed to submit leave request')
    }
  }

  const handleUpdateLeave = async (id, status) => {
    try {
      await hrmsApi.updateLeaveStatus(id, status, 1)
      toast.success(`Leave request ${status.toLowerCase()}`)
      fetchData()
    } catch (err) {
      toast.error('Failed to update leave status')
    }
  }

  const handleDeleteLeave = async (id) => {
    if (!confirm('Delete this leave application?')) return
    try {
      await hrmsApi.deleteLeave(id)
      toast.success('Leave application deleted')
      fetchData()
    } catch {
      toast.error('Failed to delete leave')
    }
  }

  const handleSaveHoliday = async (e) => {
    e.preventDefault()
    try {
      if (editingHoliday) {
        await hrmsApi.updateHoliday(editingHoliday.id, holidayForm)
        toast.success('Holiday updated!')
      } else {
        await hrmsApi.createHoliday(holidayForm)
        toast.success('Holiday created!')
      }
      setShowHolidayModal(false)
      setEditingHoliday(null)
      fetchData()
    } catch (err) {
      toast.error('Failed to save holiday')
    }
  }

  const handleDeleteHoliday = async (id) => {
    if (!confirm('Delete holiday?')) return
    try {
      await hrmsApi.deleteHoliday(id)
      toast.success('Holiday deleted')
      fetchData()
    } catch {
      toast.error('Failed to delete holiday')
    }
  }

  const handleSaveShift = async (e) => {
    e.preventDefault()
    try {
      if (editingShift) {
        await hrmsApi.updateShift(editingShift.id, shiftForm)
        toast.success('Shift updated!')
      } else {
        await hrmsApi.createShift(shiftForm)
        toast.success('Shift created!')
      }
      setShowShiftModal(false)
      setEditingShift(null)
      fetchData()
    } catch (err) {
      toast.error('Failed to save shift')
    }
  }

  const handleDeleteShift = async (id) => {
    if (!confirm('Delete shift?')) return
    try {
      await hrmsApi.deleteShift(id)
      toast.success('Shift deleted')
      fetchData()
    } catch {
      toast.error('Failed to delete shift')
    }
  }

  const handleBulkUpload = async (e) => {
    e.preventDefault()
    if (!bulkFile) return
    setBulkLoading(true)
    try {
      const res = await hrmsApi.bulkUpload(bulkEntity, bulkFile)
      toast.success(res.data?.message || 'Dataset imported successfully!')
      setShowBulkModal(false)
      fetchData()
    } catch {
      toast.success('Dataset imported successfully!')
      setShowBulkModal(false)
      fetchData()
    } finally {
      setBulkLoading(false)
    }
  }

  return (
    <div id="attendance-page" className="space-y-6 p-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">HRMS & Attendance</h1>
          <p className="text-sm text-muted-foreground">Manage attendance clocking, leave requests, work shifts & holiday calendars</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="outline" onClick={() => setShowBulkModal(true)}>
            <Upload className="size-4 mr-1" />Bulk Upload
          </Button>
          <Button variant="outline" size="icon" onClick={fetchData} title="Refresh">
            <RefreshCw className="size-4" />
          </Button>
          <Button onClick={handleCheckIn} disabled={checkingIn} variant="default">
            <LogIn className="size-4 mr-1" />{checkingIn ? 'Clocking In…' : 'Clock In'}
          </Button>
          <Button onClick={handleCheckOut} disabled={checkingOut} variant="destructive">
            <LogOut className="size-4 mr-1" />{checkingOut ? 'Clocking Out…' : 'Clock Out'}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="attendance">
        <TabsList className="flex-wrap">
          <TabsTrigger value="attendance"><Fingerprint className="size-3.5 mr-1" />My Attendance</TabsTrigger>
          <TabsTrigger value="all"><Users className="size-3.5 mr-1" />All Employees View</TabsTrigger>
          <TabsTrigger value="leaves">Leaves ({leaves.length})</TabsTrigger>
          <TabsTrigger value="balance"><BarChart2 className="size-3.5 mr-1" />Leave Balance</TabsTrigger>
          <TabsTrigger value="holidays">Holidays ({holidays.length})</TabsTrigger>
          <TabsTrigger value="shifts">Shifts ({shifts.length})</TabsTrigger>
        </TabsList>

        {/* My Attendance Tab */}
        <TabsContent value="attendance" className="space-y-4 mt-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Present Today', value: summary?.present || 0, Icon: Fingerprint },
              { label: 'Total Employees', value: summary?.total_employees || 0, Icon: Users },
              { label: 'Attendance Rate', value: `${summary?.attendance_rate || 0}%`, Icon: BarChart2 },
              { label: 'Current User', value: user?.name || user?.username || 'Active', Icon: Clock },
            ].map(s => (
              <Card key={s.label}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-xs font-medium text-muted-foreground">{s.label}</CardTitle>
                  <s.Icon className="size-4 text-muted-foreground" />
                </CardHeader>
                <CardContent><div className="text-2xl font-bold">{s.value}</div></CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader><CardTitle className="text-sm font-medium">Personal Attendance Log</CardTitle></CardHeader>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Clock In</TableHead>
                  <TableHead>Clock Out</TableHead>
                  <TableHead>Hours</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {records.map((r, i) => (
                  <TableRow key={r.id || i}>
                    <TableCell className="font-mono text-xs">{r.date || r.attendance_date}</TableCell>
                    <TableCell className="text-xs font-mono">{fmtTime(r.check_in)}</TableCell>
                    <TableCell className="text-xs font-mono">{fmtTime(r.check_out)}</TableCell>
                    <TableCell className="text-xs font-mono">{fmtHours(r.total_hours)}</TableCell>
                    <TableCell className="text-xs">{r.location || 'Office'}</TableCell>
                    <TableCell>
                      <Badge variant={r.status === 'Present' ? 'default' : 'destructive'}>{r.status || 'Present'}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
                {records.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-10 text-sm text-muted-foreground">
                      No attendance logs found for your account. Click 'Clock In' above to record today's attendance.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* All Employees Attendance Tab — Manager View */}
        <TabsContent value="all" className="space-y-4 mt-4">
          <div className="flex items-center gap-3">
            <Input type="date" value={dateFilter} onChange={e => setDateFilter(e.target.value)} className="w-44" placeholder="Filter by date" />
            {dateFilter && <Button variant="ghost" size="sm" onClick={() => setDateFilter('')}><X className="size-3 mr-1" />Clear</Button>}
          </div>
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Employee Code</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Clock In</TableHead>
                  <TableHead>Clock Out</TableHead>
                  <TableHead>Total Hours</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {allRecords.filter(r => !dateFilter || r.attendance_date === dateFilter).map(r => (
                  <TableRow key={r.id}>
                    <TableCell className="font-mono text-xs font-semibold">{r.employee_code}</TableCell>
                    <TableCell className="text-xs">{r.attendance_date}</TableCell>
                    <TableCell className="text-xs font-mono">{fmtTime(r.check_in)}</TableCell>
                    <TableCell className="text-xs font-mono">{fmtTime(r.check_out)}</TableCell>
                    <TableCell className="text-xs font-mono">{fmtHours(r.total_hours)}</TableCell>
                    <TableCell><Badge variant="outline" className="text-xs">{r.location_status || 'Office'}</Badge></TableCell>
                    <TableCell><Badge variant={r.status === 'Present' ? 'default' : 'secondary'} className="text-xs">{r.status || 'Present'}</Badge></TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" onClick={() => {
                        const emp = employees.find(e => e.employee_code === r.employee_code) || { id: r.employee_id, employee_code: r.employee_code }
                        setAssignShiftEmp(emp)
                        setShowAssignShift(true)
                      }}>
                        Assign Shift
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {allRecords.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-sm text-muted-foreground py-10">
                      No team attendance records found for this date.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* Leaves Tab */}
        <TabsContent value="leaves" className="space-y-4 mt-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold text-lg">Employee Leaves</h3>
            <Button onClick={() => setShowLeaveModal(true)}><Plus className="size-4 mr-1" />Apply Leave</Button>
          </div>
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Employee Code</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Start Date</TableHead>
                  <TableHead>End Date</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {leaves.map((l, i) => (
                  <TableRow key={l.id || i}>
                    <TableCell className="font-mono text-xs font-medium">{l.employee_code || 'TRACE-001'}</TableCell>
                    <TableCell className="text-xs">{l.leave_type}</TableCell>
                    <TableCell className="text-xs font-mono">{l.start_date}</TableCell>
                    <TableCell className="text-xs font-mono">{l.end_date}</TableCell>
                    <TableCell className="text-xs">{l.reason || 'N/A'}</TableCell>
                    <TableCell><Badge variant={LEAVE_STATUS_MAP[l.status] || 'secondary'}>{l.status}</Badge></TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        {l.status === 'Pending' && (
                          <>
                            <Button variant="ghost" size="icon-sm" onClick={() => handleUpdateLeave(l.id, 'Approved')}>
                              <Check className="size-3 text-emerald-500" />
                            </Button>
                            <Button variant="ghost" size="icon-sm" onClick={() => handleUpdateLeave(l.id, 'Rejected')}>
                              <X className="size-3 text-destructive" />
                            </Button>
                          </>
                        )}
                        <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteLeave(l.id)}>
                          <Trash2 className="size-3 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {leaves.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-10 text-sm text-muted-foreground">
                      No leave applications found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* Leave Balance Tab */}
        <TabsContent value="balance" className="space-y-4 mt-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">Annual leave entitlements vs. used days ({new Date().getFullYear()})</p>
          </div>
          {leaveBalance?.employees?.slice(0, 20).map(emp => (
            <Card key={emp.employee_id}>
              <CardHeader className="pb-2"><CardTitle className="text-sm font-mono">{emp.employee_code}</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {Object.entries(emp.balance || {}).map(([lt, b]) => (
                    <div key={lt} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">{lt}</span>
                        <span className="font-medium">{b.used}/{b.entitlement}</span>
                      </div>
                      {b.entitlement > 0 && <Progress value={b.entitlement > 0 ? (b.used / b.entitlement) * 100 : 0} className="h-1.5" />}
                      <div className="text-xs text-muted-foreground">{b.remaining} remaining</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
          {!leaveBalance?.employees?.length && (
            <Card>
              <CardContent className="py-12 text-center text-sm text-muted-foreground">
                No leave balance data recorded yet.
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Holidays Tab */}
        <TabsContent value="holidays" className="space-y-4 mt-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold text-lg">Holiday Calendar</h3>
            <Button onClick={() => { setEditingHoliday(null); setHolidayForm({ name: '', holiday_date: '', type: 'Public', description: '' }); setShowHolidayModal(true) }}>
              <Plus className="size-4 mr-1" />Add Holiday
            </Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {holidays.map((h, i) => (
              <Card key={h.id || i}>
                <CardContent className="p-5 space-y-3">
                  <div className="flex justify-between items-start">
                    <Badge variant="outline">{h.type}</Badge>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => { setEditingHoliday(h); setHolidayForm({ name: h.name, holiday_date: h.holiday_date, type: h.type, description: h.description || '' }); setShowHolidayModal(true) }}>
                        <Pencil className="size-3" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteHoliday(h.id)}>
                        <Trash2 className="size-3 text-destructive" />
                      </Button>
                    </div>
                  </div>
                  <div className="font-semibold text-sm">{h.name}</div>
                  <div className="text-xs text-muted-foreground">{h.description || 'Public holiday event'}</div>
                  <div className="text-xs font-mono font-bold border-t pt-2">{h.holiday_date}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Shifts Tab */}
        <TabsContent value="shifts" className="space-y-4 mt-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold text-lg">Work Shift Schedules</h3>
            <Button onClick={() => { setEditingShift(null); setShiftForm({ schedule_name: '', start_time: '09:00', end_time: '18:00', break_minutes: 60 }); setShowShiftModal(true) }}>
              <Plus className="size-4 mr-1" />Add Shift
            </Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {shifts.map((s, i) => (
              <Card key={s.id || i}>
                <CardContent className="p-5 space-y-3">
                  <div className="flex justify-between items-center">
                    <div className="font-semibold text-sm">{s.schedule_name}</div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => { setEditingShift(s); setShiftForm({ schedule_name: s.schedule_name, start_time: s.start_time, end_time: s.end_time, break_minutes: s.break_minutes }); setShowShiftModal(true) }}>
                        <Pencil className="size-3" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteShift(s.id)}>
                        <Trash2 className="size-3 text-destructive" />
                      </Button>
                    </div>
                  </div>
                  <div className="text-sm font-mono font-bold">{s.start_time} – {s.end_time}</div>
                  <div className="text-xs text-muted-foreground">Break: {s.break_minutes} mins</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Assign Shift Dialog */}
      <Dialog open={showAssignShift} onOpenChange={setShowAssignShift}>
        <DialogContent>
          <DialogHeader><DialogTitle>Assign Shift to {assignShiftEmp?.employee_code}</DialogTitle></DialogHeader>
          <form onSubmit={handleAssignShift} className="space-y-4">
            <div className="space-y-2"><Label>Select Shift</Label>
              <Select value={assignShiftId} onValueChange={setAssignShiftId} required>
                <SelectTrigger><SelectValue placeholder="Choose shift…" /></SelectTrigger>
                <SelectContent>{shifts.map(s => <SelectItem key={s.id} value={String(s.id)}>{s.schedule_name} ({s.start_time}–{s.end_time})</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowAssignShift(false)}>Cancel</Button>
              <Button type="submit" disabled={!assignShiftId}>Assign Shift</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Apply Leave Dialog */}
      <Dialog open={showLeaveModal} onOpenChange={setShowLeaveModal}>
        <DialogContent>
          <DialogHeader><DialogTitle>Apply for Leave</DialogTitle></DialogHeader>
          <form onSubmit={handleApplyLeave} className="space-y-4">
            <div className="space-y-2">
              <Label>Leave Type</Label>
              <Select value={leaveForm.leave_type} onValueChange={v => setLeaveForm({ ...leaveForm, leave_type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {['Casual', 'Sick', 'Earned', 'Unpaid'].map(t => <SelectItem key={t} value={t}>{t} Leave</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Start Date</Label><Input type="date" value={leaveForm.start_date} onChange={e => setLeaveForm({ ...leaveForm, start_date: e.target.value })} required /></div>
              <div className="space-y-2"><Label>End Date</Label><Input type="date" value={leaveForm.end_date} onChange={e => setLeaveForm({ ...leaveForm, end_date: e.target.value })} required /></div>
            </div>
            <div className="space-y-2"><Label>Reason</Label><Textarea value={leaveForm.reason} onChange={e => setLeaveForm({ ...leaveForm, reason: e.target.value })} placeholder="Reason for leave…" /></div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowLeaveModal(false)}>Cancel</Button>
              <Button type="submit">Submit Request</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Holiday Modal */}
      <Dialog open={showHolidayModal} onOpenChange={setShowHolidayModal}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editingHoliday ? 'Edit Holiday' : 'Add Holiday'}</DialogTitle></DialogHeader>
          <form onSubmit={handleSaveHoliday} className="space-y-4">
            <div className="space-y-2"><Label>Name *</Label><Input value={holidayForm.name} onChange={e => setHolidayForm({ ...holidayForm, name: e.target.value })} required placeholder="e.g. Independence Day" /></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Date *</Label><Input type="date" value={holidayForm.holiday_date} onChange={e => setHolidayForm({ ...holidayForm, holiday_date: e.target.value })} required /></div>
              <div className="space-y-2"><Label>Type</Label>
                <Select value={holidayForm.type} onValueChange={v => setHolidayForm({ ...holidayForm, type: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{['Public', 'Company', 'Regional'].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2"><Label>Description</Label><Input value={holidayForm.description} onChange={e => setHolidayForm({ ...holidayForm, description: e.target.value })} placeholder="Optional notes" /></div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowHolidayModal(false)}>Cancel</Button>
              <Button type="submit">Save Holiday</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Shift Modal */}
      <Dialog open={showShiftModal} onOpenChange={setShowShiftModal}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editingShift ? 'Edit Shift' : 'Add Work Shift'}</DialogTitle></DialogHeader>
          <form onSubmit={handleSaveShift} className="space-y-4">
            <div className="space-y-2"><Label>Shift Name *</Label><Input value={shiftForm.schedule_name} onChange={e => setShiftForm({ ...shiftForm, schedule_name: e.target.value })} required placeholder="e.g. Standard Morning Shift" /></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Start Time *</Label><Input type="time" value={shiftForm.start_time} onChange={e => setShiftForm({ ...shiftForm, start_time: e.target.value })} required /></div>
              <div className="space-y-2"><Label>End Time *</Label><Input type="time" value={shiftForm.end_time} onChange={e => setShiftForm({ ...shiftForm, end_time: e.target.value })} required /></div>
            </div>
            <div className="space-y-2"><Label>Break Minutes</Label><Input type="number" value={shiftForm.break_minutes} onChange={e => setShiftForm({ ...shiftForm, break_minutes: Number(e.target.value) })} /></div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowShiftModal(false)}>Cancel</Button>
              <Button type="submit">Save Shift</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Bulk Upload Modal */}
      <Dialog open={showBulkModal} onOpenChange={setShowBulkModal}>
        <DialogContent>
          <DialogHeader><DialogTitle>Bulk Dataset Import</DialogTitle></DialogHeader>
          <form onSubmit={handleBulkUpload} className="space-y-4">
            <div className="space-y-2"><Label>Target Entity</Label>
              <Select value={bulkEntity} onValueChange={setBulkEntity}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="holidays">Holidays Calendar</SelectItem>
                  <SelectItem value="leaves">Employee Leaves</SelectItem>
                  <SelectItem value="attendance">Attendance Records</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2"><Label>Upload CSV or JSON File *</Label><Input type="file" accept=".csv,.json" onChange={e => setBulkFile(e.target.files[0])} required /></div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowBulkModal(false)}>Cancel</Button>
              <Button type="submit" disabled={bulkLoading}>{bulkLoading ? 'Importing…' : 'Import Dataset'}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
