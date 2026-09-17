with open('accounts/<your-account>/config.yml', 'r') as f:
    text = f.read()

text = text.replace('!!bool "false"', 'False').replace('!!bool "true"', 'True').replace('!!int ', '')

with open('accounts/<your-account>/config.yml', 'w') as f:
    f.write(text)
