review the exsisting docs .  we want to make some chnages in this project . Initialy based on below requirements you will update all docs.overall the project features are same , but we will have a core change on platform roles , some actions of those and minor feature changes. make sure you update the docs based on below requirements which contradicts exsisting instruction and keep others same as we are not changing those .Now here are the changes--- 

1.platform role changes:
we had admin , manager , employee . One thing we want to change here is the manager :
Manager had a panel(attendence  & hr ) . Totally remove that as this is not part of task management . Manager will only   
be able to create project and assign users to this project , those users will be "project manager" (more on this below *).
there will be another feature for the  manager to view his/her project progress . 


2.Panel separation :
Currently we have a combined panel for all platforms roles . But we want to separate this based one the three hardcoded role.Regarding this : 
Admin: Admin will have base route as /admin
MAnager: Manager will have base route as /manager
Employee: Employee will have base route as /employee

Important - There will be lannding page as "/" only for guest(logedout). But loged in user we have panel based one above, auroredirect if "/" used. So we have to create a beautiful landing page.

3.Menus:
now we will redesign the menus accessible for their respective panel.
Admin:  
        Control panel - it will have all tables crud. 
        Workforce - handle the operations that are part of hrms(leaves,holidays, employees , managers,).This is not standard crud although these tables will be available on the controll panel , we will have a user end like ui for this in this workforce menu.it will have bulk upload of those tables as well as crud.
        Monitor - this will be uused for monitoring the server . 
        Configuration - mail, AI api , 
        Reports - to be discussed
         

Manager:
    no sidebar
    Actions:
        Project create(project manager assignment and removal) and progress view and progress report.
        per own project detailed view
        create project.md file by generative AI from project source files. 
    expected UI:
        only topbar with project selection. if "All" selected (which is default) shows combined dashboard and also provides feature to add new project.


Employee: 
        Project Manager -
                Expected ui - Similar project selector as platfrom manager. By default it will show similar dashboard of combined projects , their progress ,tasks,etc .
                If any project is selected then we will show the project dashboard along side task creation feature under the projeects .
        Member -
                Expected ui - Similar project selector as platfrom manager. By default it will show similar dashboard of combined projects , their progress ,tasks,etc .
                If any project is selected then we will show the project dashboard . 

** Project Tree as a graph **                










Future:
git repositoy per branch discussion
Reports part-
Project completation report, 
Employee  performance report,
Progess report(by time interval)




New requirements about project table -
        project(below is has many files):
                project_source_files(multiple file field)
        
        project(these are fields but will hold md file as github repository file urls):
                Project_initial_doc (contents about the project will be scrapped by AI from project_source_files)
                Project_doc (dupicate of Project_initial_doc, but will be updated by task completioners as project features shifts/changes or adds up)
                Progress_doc (has to be updated by task completioner)
                ProjectReport_doc (has to be updated by task completioner)
                Autometic gnatt chart creation and updation by task completion .


New requirements about project table -
        project(below is has many files):
                project_source_files(multiple file field)
        
        project(these are fields but will hold md file as github repository file urls):
                Project_initial_doc (contents about the project will be scrapped by AI from project_source_files)
                project_doc (dupicate of Project_initial_doc, but will be updated by task completioners as project features shifts/changes or adds up)
                project_progress_doc (has to be updated by task completioner)
                ProjectReport_doc (has to be updated by task completioner)
                Autometic gnatt chart creation and updation by task completion .





task management automation:
    manager step: manager brings and creates project and also uploads initial project requirement docs to project_source_files
                        ↓
    AI step: from the initial docs, scraps contents and creates project_initial_doc(project_doc will be clone of it), gantt chart.
        gantt chart - from the initial requirements, AI will create task groups (which are treated as modules for gantt chart) and will evaluate expected duration, thus the gantt chart is created.
        
                    ↓
    project manager step: 
        if required project manager will add detailed features to project doc which will be added on project_doc, thus AI will again evaluate gantt chart.
        assinging a memeber means assigning the member to the github ticket(the task in our system)
    Automation: 
        - when a project is created by manager, manager will click on "Evaluate Project" button which will trigger the first AI step. and AI will also suggest project managers
        for assigning to the project based on project manager's performance.
        - AI will also suggest tasks for creation on creation step. and also assignees.
        - project manager when creating task(task creation meaning creating a github ticket), AI will suggest members for assigning to the task based on task performance of the employees.
        - whenever task gets updated by either it is completed or due (based on statuses) or features are updated on project_doc, AI will automatically re-evaluate the gantt chart.
        - whenever task is created, a new tasks.task_progress_doc will be also created by AI which will include what to be done in detailed steps and also completion status.
        - weekly automation: from tasks.task_progress_doc, AI will evaluate from those docs from db and will update project project_progress_doc.

        - when codes are pushed on tasks to repo, obviously github will trigger ci/cd***, so we have to implement ci/cd to trigger our server and notify if cd is done successfully, then AI will auto update the task**** status.
        so member can not mark a task done. but project manager can because ci/cd is also a task which can not be marked as done as it is before the ci/cd system trigger which performs AI action to update the task status.


*** ci/cd implementation is also a task.
**** a push can also contain multiple task, so we have mark accordingly.


rest of the features:
    - task due notification
    - assignemnt notifcaion
    - completion notification as completion is marked by system
    - discussion feature per task (between task assignees and assigner)
