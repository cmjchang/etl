select *, 'https://assets.publishing.service.gov.uk/media/6aad4b1ef1f8d2a39605fa1b/df_VEH0160_UK.csv' as source_file, current_timestamp as loaded_at
from read_csv('https://assets.publishing.service.gov.uk/media/6aad4b1ef1f8d2a39605fa1b/df_VEH0160_UK.csv', header=true, all_varchar=true)
