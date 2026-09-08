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
         







Future:
git repositoy per branch discussion
Reports part-
Project completation report, 
Employee  performance report,
Progess report(by time interval)

