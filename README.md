# Fashion World

## Summary
This project is to leverage different technologies that allow consistency in data, automate decisions based on audits and report the current status of audits, and model performance

## Context
fashionworld is a retail seller, it sends order to his many suppliers and recieves their products to be sold to fashionworld clients. fashionworld operations entail a wharehouse where they audit, store and ship products.

They are constantly checkin their providers to adhere to their specifications on how they should fold and package their products. In which proactively they send `Density Reports` whenever they add new products.

Some of the painpoints fashionworld has is that data is difficult to manage, so audits are slow and unavailable during audit, and also suppliers send their products as they see fit since they did not recieve the `Density Report` on time for shipment. Also it impacts the score the supplier has and sometimes the audits miss some of the products and at the end it impacts fashionworld clients.

The plan is to develop KPIs for suppliers to adhere, calcualte the impact and predict whenever a product will have a defect (not following the suggested package quantity, folding and layout).

## Technologies
- Nifi
- Ollama
- MariaDB
- Minio
- Fastapi
- Tableu

## Workflow
Here goes a diagram

## Dashboard example

## How does it works
  1. run docker-compose
  2. install Tableau Desktop with MariaDB plugin

## Value added propositions
 - LLM reads and saves data from providers and customers
 - Automated reporting
 - Automated issue documentation
 - Automated reminders
 - Makes data uniform and saves evidence from proviers message
 - Audit information is saved and can be reviewed
 - Have information in realtime to make decisions e.g.
   - Who is performing bad, good?
   - How many units were shipped and recieved feedback from customers?
   - How many units were found with bad quality packaging
   - What is our most expensive rework
   - How much we have spent in rework
   - What are our top causes of rework
 - Create a model to predict if there is a high chance that product has a defect

