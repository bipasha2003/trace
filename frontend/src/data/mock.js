/**
 * TRACE — Mock Data
 * Realistic sample data for the management panel
 */

export const employees = [
  { id: 1, name: 'Arjun Mehta', email: 'arjun@trace.io', role: 'Frontend Developer', department: 'Engineering', status: 'active', avatar: null, joinDate: '2024-03-15', productivity: 92 },
  { id: 2, name: 'Priya Sharma', email: 'priya@trace.io', role: 'UI/UX Designer', department: 'Design', status: 'active', avatar: null, joinDate: '2024-01-20', productivity: 88 },
  { id: 3, name: 'Rahul Gupta', email: 'rahul@trace.io', role: 'Backend Developer', department: 'Engineering', status: 'active', avatar: null, joinDate: '2023-11-08', productivity: 76 },
  { id: 4, name: 'Sneha Patel', email: 'sneha@trace.io', role: 'Project Manager', department: 'Management', status: 'active', avatar: null, joinDate: '2023-09-01', productivity: 95 },
  { id: 5, name: 'Vikram Singh', email: 'vikram@trace.io', role: 'DevOps Engineer', department: 'Engineering', status: 'on-leave', avatar: null, joinDate: '2024-06-10', productivity: 81 },
  { id: 6, name: 'Ananya Iyer', email: 'ananya@trace.io', role: 'Data Analyst', department: 'Analytics', status: 'active', avatar: null, joinDate: '2024-02-28', productivity: 87 },
  { id: 7, name: 'Karthik Nair', email: 'karthik@trace.io', role: 'QA Engineer', department: 'Engineering', status: 'active', avatar: null, joinDate: '2024-04-05', productivity: 73 },
  { id: 8, name: 'Deepika Reddy', email: 'deepika@trace.io', role: 'HR Manager', department: 'Human Resources', status: 'active', avatar: null, joinDate: '2023-07-15', productivity: 90 },
]

export const tasks = [
  { id: 1, title: 'Implement authentication flow', assignee: 'Arjun Mehta', priority: 'high', status: 'in-progress', dueDate: '2026-07-18', project: 'TRACE Web', estimatedHours: 8, loggedHours: 5, tags: ['frontend', 'auth'] },
  { id: 2, title: 'Design dashboard wireframes', assignee: 'Priya Sharma', priority: 'medium', status: 'completed', dueDate: '2026-07-12', project: 'TRACE Web', estimatedHours: 6, loggedHours: 5.5, tags: ['design', 'ui'] },
  { id: 3, title: 'Set up CI/CD pipeline', assignee: 'Vikram Singh', priority: 'high', status: 'todo', dueDate: '2026-07-20', project: 'Infrastructure', estimatedHours: 12, loggedHours: 0, tags: ['devops'] },
  { id: 4, title: 'API endpoint for reports', assignee: 'Rahul Gupta', priority: 'medium', status: 'in-progress', dueDate: '2026-07-19', project: 'TRACE API', estimatedHours: 10, loggedHours: 6, tags: ['backend', 'api'] },
  { id: 5, title: 'User onboarding survey', assignee: 'Deepika Reddy', priority: 'low', status: 'todo', dueDate: '2026-07-25', project: 'HR Portal', estimatedHours: 4, loggedHours: 0, tags: ['hr'] },
  { id: 6, title: 'Performance test suite', assignee: 'Karthik Nair', priority: 'medium', status: 'in-progress', dueDate: '2026-07-21', project: 'TRACE API', estimatedHours: 8, loggedHours: 3, tags: ['qa', 'testing'] },
  { id: 7, title: 'Analytics dashboard charts', assignee: 'Ananya Iyer', priority: 'high', status: 'in-progress', dueDate: '2026-07-17', project: 'TRACE Web', estimatedHours: 10, loggedHours: 7, tags: ['analytics', 'frontend'] },
  { id: 8, title: 'Sprint retrospective report', assignee: 'Sneha Patel', priority: 'low', status: 'completed', dueDate: '2026-07-11', project: 'Management', estimatedHours: 2, loggedHours: 1.5, tags: ['management'] },
  { id: 9, title: 'Database migration scripts', assignee: 'Rahul Gupta', priority: 'high', status: 'todo', dueDate: '2026-07-22', project: 'TRACE API', estimatedHours: 6, loggedHours: 0, tags: ['backend', 'database'] },
  { id: 10, title: 'Mobile responsive fixes', assignee: 'Arjun Mehta', priority: 'medium', status: 'todo', dueDate: '2026-07-23', project: 'TRACE Web', estimatedHours: 5, loggedHours: 0, tags: ['frontend', 'mobile'] },
]

export const attendanceRecords = [
  { id: 1, employeeId: 1, name: 'Arjun Mehta', date: '2026-07-16', checkIn: '09:02', checkOut: '18:15', status: 'present', hoursWorked: 9.2, location: 'Office — Bangalore' },
  { id: 2, employeeId: 2, name: 'Priya Sharma', date: '2026-07-16', checkIn: '09:30', checkOut: '17:45', status: 'present', hoursWorked: 8.25, location: 'Remote' },
  { id: 3, employeeId: 3, name: 'Rahul Gupta', date: '2026-07-16', checkIn: '10:15', checkOut: '19:00', status: 'late', hoursWorked: 8.75, location: 'Office — Bangalore' },
  { id: 4, employeeId: 4, name: 'Sneha Patel', date: '2026-07-16', checkIn: '08:45', checkOut: '17:30', status: 'present', hoursWorked: 8.75, location: 'Office — Mumbai' },
  { id: 5, employeeId: 5, name: 'Vikram Singh', date: '2026-07-16', checkIn: null, checkOut: null, status: 'on-leave', hoursWorked: 0, location: '—' },
  { id: 6, employeeId: 6, name: 'Ananya Iyer', date: '2026-07-16', checkIn: '09:10', checkOut: '18:30', status: 'present', hoursWorked: 9.33, location: 'Remote' },
  { id: 7, employeeId: 7, name: 'Karthik Nair', date: '2026-07-16', checkIn: null, checkOut: null, status: 'absent', hoursWorked: 0, location: '—' },
  { id: 8, employeeId: 8, name: 'Deepika Reddy', date: '2026-07-16', checkIn: '08:55', checkOut: '17:50', status: 'present', hoursWorked: 8.92, location: 'Office — Mumbai' },
]

export const weeklyAttendance = [
  { day: 'Mon', present: 7, absent: 1, late: 0 },
  { day: 'Tue', present: 6, absent: 1, late: 1 },
  { day: 'Wed', present: 7, absent: 0, late: 1 },
  { day: 'Thu', present: 5, absent: 2, late: 1 },
  { day: 'Fri', present: 6, absent: 1, late: 1 },
  { day: 'Sat', present: 3, absent: 5, late: 0 },
  { day: 'Sun', present: 0, absent: 8, late: 0 },
]

export const productivityData = [
  { week: 'W1', score: 72, tasksCompleted: 12, hoursLogged: 280 },
  { week: 'W2', score: 78, tasksCompleted: 15, hoursLogged: 310 },
  { week: 'W3', score: 74, tasksCompleted: 11, hoursLogged: 290 },
  { week: 'W4', score: 85, tasksCompleted: 18, hoursLogged: 320 },
  { week: 'W5', score: 81, tasksCompleted: 16, hoursLogged: 305 },
  { week: 'W6', score: 88, tasksCompleted: 20, hoursLogged: 335 },
]

export const departmentProductivity = [
  { department: 'Engineering', score: 82, members: 4 },
  { department: 'Design', score: 88, members: 1 },
  { department: 'Management', score: 95, members: 1 },
  { department: 'Analytics', score: 87, members: 1 },
  { department: 'Human Resources', score: 90, members: 1 },
]

export const aiInsights = [
  {
    id: 1,
    type: 'warning',
    title: 'Burnout Risk Detected',
    description: 'Arjun Mehta has logged 15% more hours than average for the past 3 weeks. Consider redistributing tasks.',
    affectedEmployee: 'Arjun Mehta',
    confidence: 87,
    timestamp: '2026-07-16T10:30:00',
  },
  {
    id: 2,
    type: 'positive',
    title: 'Productivity Spike',
    description: 'The Design team has improved output by 23% this month. Priya Sharma\'s workflow optimizations are showing results.',
    affectedEmployee: 'Priya Sharma',
    confidence: 92,
    timestamp: '2026-07-16T09:15:00',
  },
  {
    id: 3,
    type: 'suggestion',
    title: 'Task Reassignment Suggested',
    description: 'Karthik Nair\'s QA backlog is growing. Reassigning 2 low-priority items to Rahul Gupta could balance the load.',
    affectedEmployee: 'Karthik Nair',
    confidence: 78,
    timestamp: '2026-07-15T16:45:00',
  },
  {
    id: 4,
    type: 'positive',
    title: 'On-Time Delivery Streak',
    description: 'Sneha Patel has delivered all assigned tasks ahead of schedule for 6 consecutive weeks.',
    affectedEmployee: 'Sneha Patel',
    confidence: 99,
    timestamp: '2026-07-15T14:20:00',
  },
  {
    id: 5,
    type: 'warning',
    title: 'Late Check-in Pattern',
    description: 'Rahul Gupta has checked in after 10:00 AM on 4 out of 5 days this week. This pattern may indicate scheduling conflicts.',
    affectedEmployee: 'Rahul Gupta',
    confidence: 84,
    timestamp: '2026-07-16T11:00:00',
  },
  {
    id: 6,
    type: 'suggestion',
    title: 'Cross-Training Opportunity',
    description: 'Ananya Iyer shows strong frontend skills in her analytics work. Consider pairing her with the Engineering team for knowledge sharing.',
    affectedEmployee: 'Ananya Iyer',
    confidence: 71,
    timestamp: '2026-07-14T13:30:00',
  },
]

export const recentActivity = [
  { id: 1, user: 'Arjun Mehta', action: 'completed', target: 'Login page redesign', time: '2026-07-16T14:30:00' },
  { id: 2, user: 'Priya Sharma', action: 'checked-in', target: 'Office — Remote', time: '2026-07-16T09:30:00' },
  { id: 3, user: 'Sneha Patel', action: 'created', target: 'Sprint 12 Planning', time: '2026-07-16T08:45:00' },
  { id: 4, user: 'Rahul Gupta', action: 'updated', target: 'API endpoint for reports', time: '2026-07-16T11:20:00' },
  { id: 5, user: 'Ananya Iyer', action: 'completed', target: 'Data pipeline setup', time: '2026-07-16T13:15:00' },
  { id: 6, user: 'Deepika Reddy', action: 'approved', target: 'Leave request — Vikram', time: '2026-07-16T10:05:00' },
]
