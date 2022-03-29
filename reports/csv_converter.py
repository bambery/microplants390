//reads initial csv file
import pandas
df = pandas.read_csv('expert_branching.csv')
print(df)

//identifies date as string
>>> print(type(df['created_at'][0]))

//places ‘user_name’ as initial column
import pandas
df = pandas.read_csv('expert_branching.csv', index_col='user_name')
print(df)

//parses date string into pandas timestamp
import pandas
df = pandas.read_csv('expert_branching.csv', index_col='user_name', parse_dates=['created_at'])
print(df)

//display date as timestamp instead of string
>>> print(type(df['created_at'][0]))

//renames columns as easier to read labels
import pandas
df = pandas.read_csv('expert_branching.csv', 
            index_col='User', 
            parse_dates=['Date'], 
            header=0, 
            names=['User', 'User ID','Workflow Name', 'Date', 'Annotations', 'Subject ID'])
print(df)


//creates new csv file with parsed data and more user friendly spreadsheet
import pandas
df = pandas.read_csv('expert_branching.csv', 
            index_col='User', 
            parse_dates=['Date'],
            header=0, 
            names=['User', 'User ID','Workflow Name', 'Date', 'Annotations', 'Subject ID'])
df.to_csv('expert_branching_modified.csv')

filtered_df = pandas.read_csv("expert_branching_modified.csv", usecols=["User", "Date", "Annotations", "Subject ID"])
print(filtered_df)
