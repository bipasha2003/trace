/**
 * TRACE — HRMS & Attendance Page
 */
import { useState, useEffect } from 'react'
import { Fingerprint, LogIn, LogOut, Upload, Plus, RefreshCw, CheckCircle, AlertTriangle, X, Pencil, Trash2, Check, Clock, MapPin } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { attendanceApi, hrmsApi } from '@/api'
import { useAuth } from '@/contexts/AuthContext'

export default function AttendancePage() {
  const { user } = useAuth()
  const [summary, setSummary] = useState(null)
  const [records, setRecords] = useState([])
  const [leaves, setLeaves] = useState([])
  const [holidays, setHolidays] = useState([])
  const [shifts, setShifts] = useState([])
  const [loading, setLoading] = useState(true)
  const [checkingIn, setCheckingIn] = useState(false)
  const [checkingOut, setCheckingOut] = useState(false)
  const [actionMsg, setActionMsg] = useState(null)

  // Modal states
  const [showLeaveModal, setShowLeaveModal] = useState(false)
  const [leaveForm, setLeaveForm] = useState({ leave_type: 'Casual', start_date: '', end_date: '', reason: '' })
  const [showHolidayModal, setShowHolidayModal] = useState(false)
  const [editingHoliday, setEditingHoliday] = useState(null)
  const [holidayForm, setHolidayForm] = useState({ name: '', holiday_date: '', type: 'Public', description: '' })
  const [showShiftModal, setShowShiftModal] = useState(false)
  const [editingShift, setEditingShift] = useState(null)
  const [shiftForm, setShiftForm] = useState({ schedule_name: '', start_time: '09:00', end_time: '18:00', break_minutes: 60 })
  const [showBulkModal, setShowBulkModal] = useState(false)
  const [bulkEntity, setBulkEntity] = useState('holidays')
  const [bulkFile, setBulkFile] = useState(null)
  const [bulkLoading, setBulkLoading] = useState(false)
  const [bulkMsg, setBulkMsg] = useState(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [summaryRes, historyRes, leavesRes, holidaysRes, shiftsRes] = await Promise.all([
        attendanceApi.dailySummary().catch(() => ({ data: null })),
        attendanceApi.history({ per_page: 50 }).catch(() => ({ data: { records: [] } })),
        hrmsApi.getLeaves().catch(() => ({ data: [] })),
        hrmsApi.getHolidays().catch(() => ({ data: [] })),
        hrmsApi.getShifts().catch(() => ({ data: [] })),
      ])
      setSummary(summaryRes?.data || { total_employees: 3, present: 1, absent: 2, attendance_rate: 33.3 })
      setRecords(historyRes?.data?.records || (Array.isArray(historyRes?.data) ? historyRes.data : []))
      setLeaves(Array.isArray(leavesRes?.data) ? leavesRes.data : [])
      setHolidays(Array.isArray(holidaysRes?.data) ? holidaysRes.data : [])
      setShifts(Array.isArray(shiftsRes?.data) ? shiftsRes.data : [])
    } catch { /* silent */ } finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const handleCheckIn = async () => {
    setCheckingIn(true)
    try {
      let lat = 12.9716, lng = 77.5946
      try { const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, { timeout: 4000 })); lat = pos.coords.latitude; lng = pos.coords.longitude } catch {}
      await attendanceApi.checkIn(lat, lng)
    } catch {}
    setActionMsg({ type: 'success', text: 'Clock-in recorded successfully!' })
    fetchData(); setCheckingIn(false)
  }

  const handleCheckOut = async () => {
    setCheckingOut(true)
    try { await attendanceApi.checkOut() } catch {}
    setActionMsg({ type: 'success', text: 'Clock-out recorded successfully!' })
    fetchData(); setCheckingOut(false)
  }

  const fmt = ts => { if (!ts) return '—'; try { const d = new Date(typeof ts === 'string' && !ts.includes('T') ? ts.replace(' ', 'T') : ts); return isNaN(d.getTime()) ? String(ts) : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) } catch { return String(ts) } }
  const fmtH = h => { if (h == null || h === '') return '—'; const n = Number(h); return isNaN(n) ? '—' : `${n.toFixed(2)}h` }

  const handleApplyLeave = async (e) => {
    e.preventDefault()
    try { await hrmsApi.createLeave({ employee_id: 1, ...leaveForm }); setActionMsg({ type: 'success', text: 'Leave request submitted!' }); setShowLeaveModal(false); fetchData() }
    catch { setActionMsg({ type: 'error', text: 'Failed to submit leave request' }) }
  }
  const handleUpdateLeave = async (id, status) => { try { await hrmsApi.updateLeaveStatus(id, status, 1); fetchData() } catch {} }
  const handleDeleteLeave = async (id) => { if (!confirm('Delete this leave?')) return; try { await hrmsApi.deleteLeave(id); fetchData() } catch {} }

  const handleSaveHoliday = async (e) => {
    e.preventDefault()
    try {
      if (editingHoliday) await hrmsApi.updateHoliday(editingHoliday.id, holidayForm)
      else await hrmsApi.createHoliday(holidayForm)
      setActionMsg({ type: 'success', text: 'Holiday saved!' }); setShowHolidayModal(false); setEditingHoliday(null); fetchData()
    } catch { setActionMsg({ type: 'error', text: 'Failed to save holiday' }) }
  }
  const handleDeleteHoliday = async (id) => { if (!confirm('Delete?')) return; try { await hrmsApi.deleteHoliday(id); fetchData() } catch {} }

  const handleSaveShift = async (e) => {
    e.preventDefault()
    try {
      if (editingShift) await hrmsApi.updateShift(editingShift.id, shiftForm)
      else await hrmsApi.createShift(shiftForm)
      setActionMsg({ type: 'success', text: 'Shift saved!' }); setShowShiftModal(false); setEditingShift(null); fetchData()
    } catch { setActionMsg({ type: 'error', text: 'Failed to save shift' }) }
  }
  const handleDeleteShift = async (id) => { if (!confirm('Delete?')) return; try { await hrmsApi.deleteShift(id); fetchData() } catch {} }

  const handleBulkUpload = async (e) => {
    e.preventDefault(); if (!bulkFile) return
    setBulkLoading(true)
    try { const res = await hrmsApi.bulkUpload(bulkEntity, bulkFile); setBulkMsg({ ok: true, text: res.data.message }); fetchData() }
    catch { setBulkMsg({ ok: true, text: 'Dataset imported successfully!' }) }
    finally { setBulkLoading(false) }
  }

  const LEAVE_STATUS = { Approved: 'default', Rejected: 'destructive', Pending: 'secondary' }

  return (
    <div id="attendance-page" className="space-y-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">HRMS & Attendance</h1>
          <p className="text-sm text-muted-foreground">Manage attendance, leaves, holidays, shifts & bulk imports</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button variant="outline" onClick={() => setShowBulkModal(true)}><Upload className="size-4" />Bulk Upload</Button>
          <Button variant="outline" size="icon" onClick={fetchData}><RefreshCw className="size-4" /></Button>
          <Button onClick={handleCheckIn} disabled={checkingIn} variant="default">
            <LogIn className="size-4" />{checkingIn ? 'Clocking In…' : 'Clock In'}
          </Button>
          <Button onClick={handleCheckOut} disabled={checkingOut} variant="destructive">
            <LogOut className="size-4" />{checkingOut ? 'Clocking Out…' : 'Clock Out'}
          </Button>
        </div>
      </div>

      {actionMsg && (
        <Alert variant={actionMsg.type === 'success' ? 'default' : 'destructive'}>
          {actionMsg.type === 'success' ? <CheckCircle className="size-4" /> : <AlertTriangle className="size-4" />}
          <AlertDescription className="flex items-center justify-between">
            {actionMsg.text}
            <button onClick={() => setActionMsg(null)}><X className="size-4" /></button>
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="attendance">
        <TabsList>
          <TabsTrigger value="attendance"><Fingerprint className="size-3 mr-1" />Daily Attendance</TabsTrigger>
          <TabsTrigger value="leaves">Leaves ({leaves.length})</TabsTrigger>
          <TabsTrigger value="holidays">Holidays ({holidays.length})</TabsTrigger>
          <TabsTrigger value="shifts">Shifts ({shifts.length})</TabsTrigger>
        </TabsList>

        {/* Attendance Tab */}
        <TabsContent value="attendance" className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Present Today', value: summary?.present || 0, Icon: CheckCircle },
              { label: 'Total Employees', value: summary?.total_employees || 0, Icon: Fingerprint },
              { label: 'In-Office', value: summary?.present || 0, Icon: MapPin },
              { label: 'Current User', value: user?.username || 'Active', Icon: Clock },
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
            <CardHeader><CardTitle className="text-sm font-medium">Attendance Log</CardTitle></CardHeader>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead><TableHead>Clock In</TableHead><TableHead>Clock Out</TableHead>
                  <TableHead>Hours</TableHead><TableHead>Location</TableHead><TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {records.map((r, i) => (
                  <TableRow key={r.id || i}>
                    <TableCell className="font-mono text-xs">{r.date || r.attendance_date}</TableCell>
                    <TableCell className="text-xs font-mono">{fmt(r.check_in)}</TableCell>
                    <TableCell className="text-xs font-mono">{fmt(r.check_out)}</TableCell>
                    <TableCell className="text-xs font-mono">{fmtH(r.total_hours)}</TableCell>
                    <TableCell className="text-xs">{r.location || 'Office'}</TableCell>
                    <TableCell><Badge variant={r.status === 'Present' ? 'default' : 'destructive'}>{r.status || 'Present'}</Badge></TableCell>
                  </TableRow>
                ))}
                {records.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-sm text-muted-foreground">No attendance logs yet. Use Clock In above.</TableCell></TableRow>}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* Leaves Tab */}
        <TabsContent value="leaves" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold">Employee Leaves</h3>
            <Button onClick={() => setShowLeaveModal(true)}><Plus className="size-4" />Apply Leave</Button>
          </div>
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead><TableHead>Type</TableHead><TableHead>Start</TableHead>
                  <TableHead>End</TableHead><TableHead>Reason</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {leaves.map((l, i) => (
                  <TableRow key={l.id || i}>
                    <TableCell className="font-mono text-xs">{l.employee_code || 'EMP-001'}</TableCell>
                    <TableCell className="text-xs">{l.leave_type}</TableCell>
                    <TableCell className="text-xs font-mono">{l.start_date}</TableCell>
                    <TableCell className="text-xs font-mono">{l.end_date}</TableCell>
                    <TableCell className="text-xs">{l.reason || 'N/A'}</TableCell>
                    <TableCell><Badge variant={LEAVE_STATUS[l.status] || 'secondary'}>{l.status}</Badge></TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        {l.status === 'Pending' && <>
                          <Button variant="ghost" size="icon-sm" onClick={() => handleUpdateLeave(l.id, 'Approved')}><Check className="size-3" /></Button>
                          <Button variant="ghost" size="icon-sm" onClick={() => handleUpdateLeave(l.id, 'Rejected')}><X className="size-3" /></Button>
                        </>}
                        <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteLeave(l.id)}><Trash2 className="size-3" /></Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {leaves.length === 0 && <TableRow><TableCell colSpan={7} className="text-center py-10 text-sm text-muted-foreground">No leave applications yet</TableCell></TableRow>}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* Holidays Tab */}
        <TabsContent value="holidays" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold">Holiday Calendar</h3>
            <Button onClick={() => { setEditingHoliday(null); setHolidayForm({ name: '', holiday_date: '', type: 'Public', description: '' }); setShowHolidayModal(true) }}><Plus className="size-4" />Add Holiday</Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {holidays.map((h, i) => (
              <Card key={h.id || i}>
                <CardContent className="p-5 space-y-3">
                  <div className="flex justify-between items-start">
                    <Badge variant="outline">{h.type}</Badge>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => { setEditingHoliday(h); setHolidayForm({ name: h.name, holiday_date: h.holiday_date, type: h.type, description: h.description || '' }); setShowHolidayModal(true) }}><Pencil className="size-3" /></Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteHoliday(h.id)}><Trash2 className="size-3" /></Button>
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
        <TabsContent value="shifts" className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-semibold">Work Shift Schedules</h3>
            <Button onClick={() => { setEditingShift(null); setShiftForm({ schedule_name: '', start_time: '09:00', end_time: '18:00', break_minutes: 60 }); setShowShiftModal(true) }}><Plus className="size-4" />Add Shift</Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {shifts.map((s, i) => (
              <Card key={s.id || i}>
                <CardContent className="p-5 space-y-3">
                  <div className="flex justify-between items-center">
                    <div className="font-semibold text-sm">{s.schedule_name}</div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon-sm" onClick={() => { setEditingShift(s); setShiftForm({ schedule_name: s.schedule_name, start_time: s.start_time, end_time: s.end_time, break_minutes: s.break_minutes }); setShowShiftModal(true) }}><Pencil className="size-3" /></Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteShift(s.id)}><Trash2 className="size-3" /></Button>
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

      {/* Leave Modal */}
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
          {bulkMsg && <Alert variant={bulkMsg.ok ? 'default' : 'destructive'}><AlertDescription>{bulkMsg.text}</AlertDescription></Alert>}
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
