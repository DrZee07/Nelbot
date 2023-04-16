# flake8: noqa
JIRA_ISSUE_CREATE_PROMPT = \
    ("""
    This tool is a wrapper around atlassian-python-api's Jira issue_create API, useful when you need to create a Jira issue. 
    The input to this tool is a dictionary specifying the fields of the Jira issue, and will be passed into atlassian-python-api's Jira `issue_create` function.
    For example, to create a low priority task called "test issue" with description "test description", you would pass in the following dictionary: 
    {{"summary": "test issue", "description": "test description", "issuetype": {{"name": "Task"}}, "priority": {{"name": "Low"}}}}
    """)

JIRA_GET_ALL_PROJECTS_PROMPT = \
    ("""
    This tool is a wrapper around atlassian-python-api's Jira project API, 
    useful when you need to fetch all the projects the user has access to, find out how many projects there are, or as an intermediary step that involv searching by projects. 
    there is no input to this tool.
    """)

JIRA_JQL_PROMPT = \
    ("""
    This tool is a wrapper around atlassian-python-api's Jira jql API, useful when you need to search for Jira issues.
    The input to this tool is a JQL query string, and will be passed into atlassian-python-api's Jira `jql` function,
    For example, to find all the issues in project "Test" assigned to the me, you would pass in the following string:
    project = Test AND assignee = currentUser()
    or to find issues with summaries that contain the word "test", you would pass in the following string:
    summary ~ 'test'
    """)

JIRA_CATCH_ALL_PROMPT = \
    ("""
    This tool is a wrapper around atlassian-python-api's Jira API.
    There are other dedicated tools for fetching all projects, and creating and searching for issues, 
    use this tool if you need to perform any other actions allowed by the atlassian-python-api Jira API.
    The input to this tool is line of python code that calls a function from atlassian-python-api's Jira API
    For example, to update the summary field of an issue, you would pass in the following string:
    self.jira.update_issue_field(key, {{"summary": "New summary"}})
    or to find out how many projects are in the Jira instance, you would pass in the following string:
    self.jira.projects()
    For more information on the Jira API, refer to https://atlassian-python-api.readthedocs.io/jira.html
    """)
