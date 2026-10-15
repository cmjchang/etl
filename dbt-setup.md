# Data Services Platform 

## what this is 
core code for the data ervice platform. it is deployed to pre-existing cloud resources. it ingests data from 40+ source
systesm and transofrm it into analytics ready datsets on snowflake 


naming convention is "<layer>_<system>_<entity>"
views : 'vw'
ephermeral: 'eph'
lookup: 'lookup'

incremental loading
use incremental delta() in the where claude
streategies are 'append', 'delete+insert' and 'merge'
use incremental washback for late arriving data
type.2 scd have variants 
other marcos: cleaning (string, ), hashing, parsing (datetime, boolean), limit dev run
PII tag: different method of masking policy apply to the columns, 


## branching
branch name is <ticket_type>/<ticket_number>_<publisher_initial>_<ticket_description_in_camal_case>
ticket_type: feature, bug, technical_debt
ticket_number: ABC-0001
publisher_inital: JC
ticket_description_in_camal_case: AddingColumnsInDimModel

## developement