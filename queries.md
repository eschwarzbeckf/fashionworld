# List of queries to view data

Here a list of suggested queries to check the data from the database

## Check percentage audits, total units found with issues, and estimated cost
> Table with the total quantity of found issues vs total issues that were acutally shipped by providers
> Gives a total estimated impact of the cost, (my guess this relates to the rework done to the units)
> If found none, only the overhead cost is accounted
> Gives also the total cost per audit, and the total cost per unit.
```sql
select a.issue_description, count(a.issue_description) as total_issues_found, pd.total_issues, round(count(a.issue_description)/total_issues * 100,3) as percentage,round(sum(a.cost_impact),2) as estimated_cost, round(sum(a.cost_impact)/count(a.issue_description),2) as total_cost_per_audit, round(sum(a.cost_impact)/total_issues,2) as total_cost_per_unit from audits as a join (select issue, count(issue) as total_issues from products_defects group by issue) as pd on pd.issue = a.issue_description group by a.issue_description order by estimated_cost desc;
```
--------