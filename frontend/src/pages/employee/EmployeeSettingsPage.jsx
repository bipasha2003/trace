import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, User, BellRing, ShieldCheck, Palette as PaletteIcon, Save as SaveIcon, Sun as SunIcon, Moon as MoonIcon, CheckCircle, AlertTriangle, Pencil } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme } from '@/contexts/ThemeContext'
import { authApi } from '@/api'

export default function SettingsPage() {
  const { user, updateUser } = useAuth()
  const { mode, toggleMode } = useTheme()
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)
  const [profileForm, setProfileForm] = useState({ name: '', phone: '', gender: '', github_username: '' })
  const [notifications, setNotifications] = useState({
    email_task: true, email_attendance: true, email_reports: false,
    push_task: true, push_attendance: false,
  })

  useEffect(() => {
    if (user) setProfileForm({ name: user.name || '', phone: user.phone || '', gender: user.gender || '', github_username: user.github_username || '' })
  }, [user])

  const handleSaveProfile = async () => {
    setSaving(true); setMsg(null)
    try {
      const res = await authApi.updateProfile(user.id, {
        name: profileForm.name || undefined,
        phone: profileForm.phone || undefined,
        gender: profileForm.gender || undefined,
        github_username: profileForm.github_username.trim(),
      })
      updateUser(res.data)
      setMsg({ type: 'success', text: 'Profile updated successfully!' })
    } catch (err) {
      setMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to update profile' })
    } finally { setSaving(false) }
  }

  const handleSaveNotifications = () => {
    localStorage.setItem('trace_notifications', JSON.stringify(notifications))
    setMsg({ type: 'success', text: 'Notification preferences saved!' })
  }

  const initials = (user?.name || 'U').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()

  return (
    <div id="settings-page" className="space-y-6 max-w-[900px]">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <SettingsIcon className="size-5 text-muted-foreground" /> Settings
        </h1>
        <p className="text-sm text-muted-foreground">Manage your account and preferences</p>
      </div>

      {msg && (
        <Alert variant={msg.type === 'success' ? 'default' : 'destructive'}>
          {msg.type === 'success' ? <CheckCircle className="size-4" /> : <AlertTriangle className="size-4" />}
          <AlertDescription>{msg.text}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="profile" onValueChange={() => setMsg(null)}>
        <TabsList>
          <TabsTrigger value="profile"><User className="size-3 mr-1" />Profile</TabsTrigger>
          <TabsTrigger value="notifications"><BellRing className="size-3 mr-1" />Notifications</TabsTrigger>
          <TabsTrigger value="security"><ShieldCheck className="size-3 mr-1" />Security</TabsTrigger>
          <TabsTrigger value="appearance"><PaletteIcon className="size-3 mr-1" />Appearance</TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile">
          <Card>
            <CardHeader><CardTitle className="text-sm">Profile Information</CardTitle></CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50">
                <Avatar className="size-12">
                  <AvatarFallback>{initials}</AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="font-medium">{user?.name || '—'}</div>
                  <div className="text-xs text-muted-foreground">{user?.email}</div>
                  <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                    {user?.roles?.map((r) => <Badge key={r} variant="secondary">{r}</Badge>)}
                    <Badge variant={user?.is_verified ? 'default' : 'secondary'}>
                      {user?.is_verified ? 'Verified' : 'Unverified'}
                    </Badge>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="s-name">Full Name</Label>
                  <Input id="s-name" value={profileForm.name} onChange={e => setProfileForm({ ...profileForm, name: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="s-phone">Phone</Label>
                  <Input id="s-phone" type="tel" placeholder="+91-9876543210" value={profileForm.phone} onChange={e => setProfileForm({ ...profileForm, phone: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="s-github">GitHub username</Label>
                  <Input id="s-github" placeholder="octocat" value={profileForm.github_username} onChange={e => setProfileForm({ ...profileForm, github_username: e.target.value })} />
                  <p className="text-xs text-muted-foreground">Needed so the GitHub issues for your tasks can be assigned to you.</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="s-email">Email</Label>
                  <Input id="s-email" type="email" value={user?.email || ''} disabled />
                </div>
                <div className="space-y-2">
                  <Label>Gender</Label>
                  <Select value={profileForm.gender} onValueChange={v => setProfileForm({ ...profileForm, gender: v })}>
                    <SelectTrigger><SelectValue placeholder="Prefer not to say" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Prefer not to say</SelectItem>
                      <SelectItem value="Male">Male</SelectItem>
                      <SelectItem value="Female">Female</SelectItem>
                      <SelectItem value="Non-binary">Non-binary</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Button onClick={handleSaveProfile} disabled={saving}>
                {saving ? <span className="size-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" /> : <SaveIcon className="size-4" />}
                Save Changes
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications">
          <Card>
            <CardHeader><CardTitle className="text-sm">Notification Preferences</CardTitle></CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Email Notifications</p>
                {[
                  { key: 'email_task', label: 'Task assignments & updates' },
                  { key: 'email_attendance', label: 'Attendance reminders' },
                  { key: 'email_reports', label: 'Weekly productivity reports' },
                ].map(item => (
                  <div key={item.key} className="flex items-center justify-between">
                    <Label className="font-normal">{item.label}</Label>
                    <Switch checked={notifications[item.key]} onCheckedChange={v => setNotifications({ ...notifications, [item.key]: v })} />
                  </div>
                ))}
              </div>
              <Separator />
              <div className="space-y-4">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Push Notifications</p>
                {[
                  { key: 'push_task', label: 'Task deadline reminders' },
                  { key: 'push_attendance', label: 'Check-in/out alerts' },
                ].map(item => (
                  <div key={item.key} className="flex items-center justify-between">
                    <Label className="font-normal">{item.label}</Label>
                    <Switch checked={notifications[item.key]} onCheckedChange={v => setNotifications({ ...notifications, [item.key]: v })} />
                  </div>
                ))}
              </div>
              <Button onClick={handleSaveNotifications}><SaveIcon className="size-4" />Save Preferences</Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security">
          <Card>
            <CardHeader><CardTitle className="text-sm">Security Settings</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {[
                { title: 'Password', sub: 'Last changed: Never', action: <Button variant="outline" size="sm"><Pencil className="size-3" />Change</Button> },
                { title: 'Two-Factor Authentication', sub: 'Add an extra layer of security', action: <Badge variant="secondary">Not Enabled</Badge> },
                { title: 'Active Sessions', sub: '1 active session on this device', action: <Badge>Current</Badge> },
              ].map(item => (
                <div key={item.title} className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                  <div>
                    <div className="text-sm font-medium">{item.title}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{item.sub}</div>
                  </div>
                  {item.action}
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Appearance Tab */}
        <TabsContent value="appearance">
          <Card>
            <CardHeader><CardTitle className="text-sm">Appearance</CardTitle></CardHeader>
            <CardContent className="space-y-6">
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">Theme Mode</p>
                <div className="flex gap-3">
                  {[{ key: 'dark', label: 'Dark', Icon: MoonIcon }, { key: 'light', label: 'Light', Icon: SunIcon }].map(({ key, label, Icon }) => (
                    <Button
                      key={key}
                      variant={mode === key ? 'default' : 'outline'}
                      onClick={toggleMode}
                      className="flex items-center gap-2"
                    >
                      <Icon className="size-4" /> {label}
                      {mode === key && <CheckCircle className="size-3" />}
                    </Button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
