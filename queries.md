# List of queries to view data

Here a list of suggested queries to check the data from the database

## Check percentage audits, total units found with issues, and estimated cost
> Table with the total quantity of found issues vs total issues that were acutally shipped by providers
> Gives a total estimated impact of the cost, (my guess this relates to the rework done to the units)
> If found none, only the overhead cost is accounted
> Gives also the total cost per audit, and the total cost per unit.
> 
_Query:_
```sql
select a.issue_description, count(a.issue_description) as total_issues_found, pd.total_issues, round(count(a.issue_description)/total_issues * 100,3) as percentage,round(sum(a.cost_impact),2) as estimated_cost, round(sum(a.cost_impact)/count(a.issue_description),2) as total_cost_per_audit, round(sum(a.cost_impact)/total_issues,2) as total_cost_per_unit from audits as a join (select issue, count(issue) as total_issues from products_defects group by issue) as pd on pd.issue = a.issue_description group by a.issue_description order by estimated_cost desc;
```
--------
## Check percentage audits, total units forun with issues and estimated cost per supplier and issue
> Shows all of the suppliers products with issues that were created and also audited and adds a cost to them
>
_Query:_
``` sql
select s.name, a.issue_description, count(a.issue_description) as issues_found,total_issues,round(count(a.issue_description)/total_issues * 100,3) as percentage_found, round(sum(a.cost_impact),2) as estimated_cost, round(sum(a.cost_impact)/count(a.issue_description),2) as cost_per_audit, round(sum(a.cost_impact)/total_issues,2) as cost_per_unit from audits as a join suppliers_products as sp on a.product_id = sp.product_id join suppliers as s on sp.supplier_id = s.supplier_id join (select s.name,issue,count(issue) as total_issues from products_defects as pd join suppliers_products as sp on pd.product_id = sp.product_id join suppliers as s on s.supplier_id = sp.supplier_id group by s.name, issue) as pd on pd.issue = a.issue_description and pd.name = s.name group by s.name, a.issue_description order by s.name,issues_found desc;
```
--------
## Check percentage audits, total units forun with issues and estimated cost per supplier and issue WITHOUT none issues
> Shows all of the suppliers products with issues that were created and also audited and adds a cost to them, _**WITHOUT**_ any _"none"_ found issues
>
```sql
select s.name, a.issue_description, count(a.issue_description) as issues_found,total_issues,round(count(a.issue_description)/total_issues * 100,3) as percentage_found, round(sum(a.cost_impact),2) as estimated_cost, round(sum(a.cost_impact)/count(a.issue_description),2) as cost_per_audit, round(sum(a.cost_impact)/total_issues,2) as cost_per_unit from audits as a join suppliers_products as sp on a.product_id = sp.product_id join suppliers as s on sp.supplier_id = s.supplier_id join (select s.name,issue,count(issue) as total_issues from products_defects as pd join suppliers_products as sp on pd.product_id = sp.product_id join suppliers as s on s.supplier_id = sp.supplier_id group by s.name, issue) as pd on pd.issue = a.issue_description and pd.name = s.name where a.issue_description != "none" group by s.name, a.issue_description order by s.name,issues_found desc;
```
--------
## Check percentage auidts, total units with issues removing the none found issues per supplier
> Shows how many units per supplier were found, without considering the "none" issues
>
_Query:_
```sql
select s.name, count(a.issue_description) as issues_found,total_issues,round(count(a.issue_description)/total_issues * 100,3) as percentage_found, round(sum(a.cost_impact),2) as estimated_cost, round(sum(a.cost_impact)/count(a.issue_description),2) as cost_per_audit, round(sum(a.cost_impact)/total_issues,2) as cost_per_unit from audits as a join suppliers_products as sp on a.product_id = sp.product_id join suppliers as s on sp.supplier_id = s.supplier_id join (select s.name,count(issue) as total_issues from products_defects as pd join suppliers_products as sp on pd.product_id = sp.product_id join suppliers as s on s.supplier_id = sp.supplier_id group by s.name) as pd on pd.name = s.name where a.issue_description != "none" group by s.name order by s.name;
```
--------
## Check cost of all audits and results of audits
> Shows the status of the audits, the cost impact of each audit
>
_Query:_
```sql
select r.order_id, round(sum(cost_impact),2) as cost_impact, sum(o.boxes_ordered) as total_boxes, o.order_status from receptions as r left join audits as a on r.package_uuid = a.package_uuid join orders as o on o.order_id = r.order_id and r.product_id = o.product_id group by r.order_id, o.order_status;
```