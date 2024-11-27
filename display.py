from app import app, db, User
from prettytable import PrettyTable
app.app_context().push()
db.create_all()
users = User.query.all()

# for user in users:
#     print(str(user.id)  + " " + user.email + " " + user.role)
    
table = PrettyTable()
table.field_names = ["ID", "EMAIL", "ROLE"]
for user in users:
    table.add_row([user.id, user.email, user.role])
# print(User.query_class().all())

print(table)
