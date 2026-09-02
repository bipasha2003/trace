# Project Scope:-
our project starts after employe is already in the system and ends at task completion + evaluation and reporting.

## Can not escape:-
As our syste starts after employee exsistance but we can not escape the bellow things:
- Employe tracking requirements form hrms(bare minimun)
    - Attendence
    - Employe leaves
    - Employee shifts
    - holiday

## Auth source & Roles:-

### Auth source is user
#### Role-- Admin , Employee, manager

#### task level roles:
Fixed: project manager(task has many project managers which are basicaly users)
      ↓
      team leads
      ↓
      members

## Employee tracking for task management:
even if we just manage task but the system needs some employe information and employe attandence leaves, holidays, shifts , so that the system properly recomends or helps with task assignment and task evaluation. So lets just create a crud for these tables and also recomends if any other table sare requred whichh are not part of task management system but falls under closely coupled hrms also add a small featur for bulk uploading for these . Also add clock in and out feature in this bareminimun requirements and not part of trace .

## Task Management:

### task Assignment ovrview as a template flow---
Manager (user role) out of our scope gets and creates a task in the system and assigns one or multiple project managers(task level role) → now comes the intratinting part , the main parent task can be devided upto infinite child tasks, so the team leads and members will also rotate on each levels . As an example :
                          Task 1 (project manager)
                            ↓
                      ---------------
                      ↓              ↓
           (team 1) task 1.1        task 1.2 (team 2 -- team lead assigned and memebers assigned under the team task)
                      ↓
             -----------------------------
             ↓                            ↓
        Team 1.1(task1.1.1)           Team 1.2 (task 1.1.2 -- team lead assigned and memebers assigned under the team task)
             ↓
             .
             .
             .
↓             upto members assigned

### task work ---
- whenevr a groound level task is created and member assigned, the task is pushed to git hub api issues and memebers also assigned there.
- It is recomended for a member to always push wwith the issue id (github issue id).
- LLM will verify the commit with the ground level task . 
- Maybe system will auto trigger report to team lead , like this when all grund level task under a team is  complited ,another report will be trigger t to it parent and so on.
- Finally there wil be ovbouly evaluation on the work  completion etc. as a standard task managment feature.
- Project wise autocreate messgae group , and when ever team lead or  member based on the  infinite tree is assigned , it is auto added to the group . There will be some rule inforcement based on th tree for who can tag someone ora team or parent or members or comunicate insite the group.