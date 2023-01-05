# MEF MOOC Platform Backend

## Project Description

MOOC courses are courses which are taken from online course platforms such as Coursera, edX etc. and are required for graduation at MEF University. All departments have different amounts of free electives and hum-soc elective courses inside and there are coordinators who are responsible for a department’s MOOC course processes. Each student finds courses for a specific course and creates bundles for taking credits from the course. These bundles must be approved by the coordinator and then students can start and finish the courses. When courses are finished, certificates are shared by the coordinator and the coordinator decides to pass or fail. But this system doesn’t have a platform that provides checking all of those processes by both students and coordinators. Blackboard, gmail, and some google sheets are used to collect all those processes. To collect all of the processes in a single platform can provide benefits for both coordinators and students. In this project, it is aimed to create a relational database for the project in a way which has the correct story and as much as without redundancy. Database creation is one of the most crucial steps for the project but in addition to this project’s backend and frontend implementations were designed. In this report, all processes for the database design and implementations according to the need are explained in detail. PostgreSQL was used in this project.

## Steps

1) Insert your own database information for the following values in config.py

> DATABASE_HOST
> 
> DATABASE_NAME
> 
> DATABASE_USER
> 
> DATABASE_PASSWORD

2) Run the following code to create the tables
```
python models.py
```

3) Run the following code
```
python main.py
```
