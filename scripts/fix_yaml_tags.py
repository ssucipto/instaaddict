with open('accounts/lolatheozjack/config.yml', 'r') as f:
    text = f.read()

text = text.replace('!!bool "false"', 'False').replace('!!bool "true"', 'True').replace('!!int ', '')

with open('accounts/lolatheozjack/config.yml', 'w') as f:
    f.write(text)
