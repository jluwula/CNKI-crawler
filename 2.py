import pymysql

# 数据区
DBHOST = "localhost"
DBUSER = "root"
DBPASS = "123456"
DBNAME = "p2a"


# 函数区
# 获取论文-作者关系 返回的数据为元组
def getPap2Au(db):
    cur = db.cursor()
    sql = "select paperName, author_name from paper2au;"
    cur.execute(sql)
    pap2au = cur.fetchall()
    return pap2au


# 获取作者-机构关系
def getAu2Instu(db):
    cur = db.cursor()
    sql = "select author_name, institution_name from au2institution;"
    cur.execute(sql)
    au2instu = cur.fetchall()
    return au2instu


# 获取论文-机构关系
def getPap2Instu(db):
    cur = db.cursor()
    sql = "select paperName, institution_name from paper2institution;"
    cur.execute(sql)
    pap2instu = cur.fetchall()
    return pap2instu


# 转换为三元组(论文-作者)
def transfer_Pap_Au(pap2au):
    AuthorIs = []
    for p2a in pap2au:
        str = (p2a[0], "作者为", p2a[1])
        AuthorIs.append(str)
    return AuthorIs


# 转换为三元组(作者-机构)
def transfer_Au_institution(au2instu):
    WorkIn = []
    for a2i in au2instu:
        str = (a2i[0], "工作于", a2i[1])
        WorkIn.append(str)
    return WorkIn


# 转换为三元组（论文-机构）
def transfer_pap_institution(pap2instu):
    FunctionIs = []
    for p2i in pap2instu:
        str = (p2i[0], "发表机构为", p2i[1])
        FunctionIs.append(str)
    return FunctionIs


if __name__ == "__main__":
    db = pymysql.connect(user=DBUSER, password=DBPASS, host=DBHOST, database=DBNAME)
    pap2au = getPap2Au(db=db)
    pap2instu = getPap2Instu(db = db)
    au2instu = getAu2Instu(db = db)
    AuthorIs = transfer_Pap_Au(pap2au=pap2au)
    WorkIn = transfer_Au_institution(au2instu=au2instu)
    FunctionIs = transfer_pap_institution(pap2instu=pap2instu)
    print(AuthorIs)
    print(WorkIn)
    print(FunctionIs)
