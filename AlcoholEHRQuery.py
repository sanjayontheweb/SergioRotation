# %%
import pymssql
import pandas as pd
import configparser
import matplotlib.pyplot as plt
from psmpy import PsmPy
import numpy as np
from tqdm import tqdm

from dateutil.relativedelta import relativedelta

# %%
#Set up OMOP database connection

config = configparser.ConfigParser()
config.read('omop_db_config_new.ini')

db_host = config['database']['host']
db_user = config['database']['user']
db_password = config['database']['password']
db_name = config['database']['dbname']

sql_conn = pymssql.connect(db_host, db_user, db_password, db_name)
cursor = sql_conn.cursor(as_dict=True)

# %%
#Functions to query db
def get_data(sql_conn, query):
    cursor = sql_conn.cursor(as_dict=True)
    cursor.execute(query)
    results = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    df = pd.DataFrame(results, columns=columns)
    return df

def run_query(sql_conn, query):
    cursor = sql_conn.cursor(as_dict=True)
    cursor.execute(query)
    return None

# %% [markdown]
# # Motivation 2: Alcohol Addiction as Positive Control
# 
# ## Defining alc_dependent and not_alc_dependent

# %%
#Find all events where alcohol dependence was diagnosed— Includes these conditions
# concept_id	concept_name
# 435243	Alcohol dependence
# 36713086	Alcohol induced disorder co-occurrent and due to alcohol dependence
# 37017563	Severe alcohol dependence
# 37018356	Moderate alcohol dependence
# 45757093	Alcohol dependence in pregnancy

drop_table_query = """DROP TABLE IF EXISTS #alc_dep_population"""

alc_dep_pop_query = """
WITH ConditionFrequency AS (
    SELECT 
        [person_id],
        [condition_concept_id],
        COUNT(*) AS [condition_frequency],
        ROW_NUMBER() OVER (PARTITION BY [person_id] ORDER BY COUNT(*) DESC) AS rn
    FROM [condition_occurrence]
    WHERE [condition_concept_id] IN 
        (SELECT [concept_id]
         FROM [concept]
         WHERE [concept_name] LIKE '%alcohol dependence%'
         AND [domain_id] = 'Condition')
    GROUP BY [person_id], [condition_concept_id]
),
DiagnosisDetails AS (
    SELECT 
        [person_id],
        MIN([condition_start_date]) AS [first_diagnosis_date],
        MAX([condition_start_date]) AS [last_diagnosis_date],
        COUNT([visit_occurrence_id]) AS [n_visits]
    FROM [condition_occurrence]
    WHERE [condition_concept_id] IN 
        (SELECT [concept_id]
         FROM [concept]
         WHERE [concept_name] LIKE '%alcohol dependence%'
         AND [domain_id] = 'Condition')
    GROUP BY [person_id]
    HAVING COUNT([visit_occurrence_id]) >= 2
),
FirstPatientVisit AS (
    SELECT
        [person_id],
        MIN([visit_start_date]) AS [first_visit]
    FROM [visit_occurrence]
    GROUP BY [person_id]
)
SELECT 
    d.[person_id],
    fpv.[first_visit],
    d.[first_diagnosis_date],
    d.[n_visits],
    cf.[condition_concept_id] AS [most_frequent_condition]
INTO
    #alc_dep_population
FROM 
    DiagnosisDetails d
JOIN 
    ConditionFrequency cf
ON 
    d.[person_id] = cf.[person_id]
JOIN
    FirstPatientVisit fpv
ON
    d.[person_id] = fpv.[person_id]
WHERE 
    cf.rn = 1;
"""

run_query(sql_conn, drop_table_query)
run_query(sql_conn, alc_dep_pop_query)

# %%
#Ensure that their records go back at least 6 months before their first diagnosis
query = """
SELECT a.*
FROM #alc_dep_population a
WHERE EXISTS (
    SELECT 1
    FROM observation obs
    WHERE a.person_id = obs.person_id
    AND obs.observation_date <= DATEADD(MONTH, -6, a.first_diagnosis_date)
)
"""

alc_dep_pop = get_data(sql_conn, query)

# %%
alc_dep_pop

# %% [markdown]
# ## Create control

# %%
#Grabbing top 20x5438 (# cases) to allow sufficient PSM

drop_control_table_query = """DROP TABLE IF EXISTS #control_population"""

control_pop_query = """
WITH AlcoholDependencePatients AS (
    SELECT DISTINCT
        [person_id]
    FROM [condition_occurrence]
    WHERE [condition_concept_id] IN 
        (SELECT [concept_id]
         FROM [concept]
         WHERE [concept_name] LIKE '%alcohol dependence%'
         AND [domain_id] = 'Condition')
),
EligibleControls AS (
    SELECT
        [person_id],
        COUNT([visit_occurrence_id]) AS [n_visits]
    FROM [visit_occurrence]
    WHERE [person_id] NOT IN (SELECT [person_id] FROM AlcoholDependencePatients)
    GROUP BY [person_id]
    HAVING COUNT([visit_occurrence_id]) >= 10
),
ControlSample AS (
    SELECT 
        [person_id]
    FROM EligibleControls
    ORDER BY NEWID() -- Randomly select controls
    OFFSET 0 ROWS
    FETCH NEXT (5478 * 20) ROWS ONLY
),
ControlDetails AS (
    SELECT 
        ecs.[person_id],
        MIN(vo.[visit_start_date]) AS [first_patient_visit],
        MAX(vo.[visit_start_date]) AS [last_visit_date],
        COUNT(vo.[visit_occurrence_id]) AS [n_visits]
    FROM 
        ControlSample ecs
    JOIN 
        [visit_occurrence] vo
    ON 
        ecs.[person_id] = vo.[person_id]
    GROUP BY 
        ecs.[person_id]
),
ControlWithSixMonths AS (
    SELECT
        cd.[person_id],
        cd.[first_patient_visit],
        cd.[n_visits]
    FROM 
        ControlDetails cd
    WHERE EXISTS (
        SELECT 1
        FROM [visit_occurrence] vo
        WHERE cd.[person_id] = vo.[person_id]
        AND vo.[visit_start_date] >= DATEADD(MONTH, 6, cd.[first_patient_visit])
    )
)
SELECT
    cwsm.[person_id],
    cwsm.[first_patient_visit],
    cwsm.[n_visits]
FROM
    ControlWithSixMonths cwsm;
"""

run_query(sql_conn, drop_control_table_query)

alc_control_pop = get_data(sql_conn, control_pop_query)



# %%
alc_dep_pop

# %%
alc_control_pop

# %% [markdown]
# # Add Age, Sex Data for PSM

# %%
# Create Table with alcohol dependence patient IDs
alc_dep_ids = alc_dep_pop['person_id'].to_list()
alc_dep_ids = '), ('.join([str(subject_id) for subject_id in alc_dep_ids])
alc_dep_ids = '(' + alc_dep_ids + ')'
alc_dep_ids = alc_dep_ids.split(', ')

query_alc_dep_ids = f"""
DROP TABLE IF EXISTS #alc_dep_patient_ids;
CREATE TABLE #alc_dep_patient_ids (person_id INT);
"""

for subject_id in alc_dep_ids:
    query_alc_dep_ids += f"""
    INSERT INTO #alc_dep_patient_ids (person_id)
    VALUES {subject_id};
    """

run_query(sql_conn, query_alc_dep_ids)

# Create Table with control population patient IDs
control_ids = alc_control_pop['person_id'].to_list()
control_ids = '), ('.join([str(subject_id) for subject_id in control_ids])
control_ids = '(' + control_ids + ')'
control_ids = control_ids.split(', ')

query_control_ids = f"""
DROP TABLE IF EXISTS #control_patient_ids;
CREATE TABLE #control_patient_ids (person_id INT);
"""

for subject_id in control_ids:
    query_control_ids += f"""
    INSERT INTO #control_patient_ids (person_id)
    VALUES {subject_id};
    """

run_query(sql_conn, query_control_ids)

# Add age and sex info to alcohol dependence table
alc_dep_bio_query = """
SELECT
    p.person_id, 
    p.gender_source_value, 
    2024 - p.year_of_birth AS age, 
    p.ethnicity_source_value
FROM
    #alc_dep_patient_ids ad
    JOIN [person] p
        ON ad.person_id = p.person_id
"""

alc_dep_pop = alc_dep_pop.merge(get_data(sql_conn, alc_dep_bio_query), on='person_id', how='left')

# Add age and sex info to control table
control_bio_query = """
SELECT
    p.person_id, 
    p.gender_source_value, 
    2024 - p.year_of_birth AS age, 
    p.ethnicity_source_value
FROM
    #control_patient_ids cp
    JOIN [person] p
        ON cp.person_id = p.person_id
"""

alc_control_pop = alc_control_pop.merge(get_data(sql_conn, control_bio_query), on='person_id', how='left')

# %%
alc_dep_pop

# %% [markdown]
# # Perform PSM on Age, Sex, ethnicity_source_value

# %%
# Add a 'dependent' column to identify alcohol dependence cases
alc_dep_pop['dependent'] = 1
alc_control_pop['dependent'] = 0

# Concatenate alcohol dependence and control populations into a single DataFrame
full_bio_cohort = pd.concat([alc_dep_pop, alc_control_pop], axis=0, ignore_index=True)

# Convert gender to numerical values
full_bio_cohort['gender_source_value'] = full_bio_cohort['gender_source_value'].map({'Male': 0, 'Female': 1}).fillna(2).astype(int)

# Convert gender to numerical values
full_bio_cohort['gender_source_value'] = full_bio_cohort['gender_source_value'].map({'Male': 0, 'Female': 1}).fillna(2).astype(int)

#Convert ethnicity to numerical values
full_bio_cohort['ethnicity_source_value'] = pd.factorize(full_bio_cohort['ethnicity_source_value'])[0]

# Create an instance of PsmPy with the relevant columns
prop_sm = PsmPy(full_bio_cohort[['person_id', 'gender_source_value', 'age', 'dependent', 'ethnicity_source_value']], treatment='dependent', indx='person_id')

# Calculate the propensity scores based on sex, age, and other relevant variables
prop_sm.logistic_ps(balance=True)

# Perform matching, with a ratio of 8 controls to each dependent subject
prop_sm.knn_matched_12n(matcher='propensity_logit', how_many=4)

# List of final ids for cohort, after matching
final_cohort_ids = prop_sm.matched_ids.values.ravel()

# %%
prop_sm.matched_ids

# %%
prop_sm.effect_size_plot(save=True)

# %%
#save the ids list so don't need to re-run PSM
prop_sm.matched_ids.to_feather("data/alcohol_cohort_ids.feather")

# %%



