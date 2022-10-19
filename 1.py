# coding=gbk
import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from py2neo import *
from urllib.parse import urljoin
import pymysql

# 数据区
Legal_list = ['国际期刊', '期刊', '硕士', '博士']
Driver_Path = "D:/下载/chromedriver103.exe" # 驱动地址，根据实际情况修改
query = "AF=吉林大学软件学院 OR AF=吉林大学计算机科学与技术学院"
DBHOST = "localhost"
DBUSER = "root"
DBPASS = "123456"
DBNAME = "p2a"
stimulate_times = 100
Pap2Au = []
Au2Institution = []
Pap2Institution = []
count = 0
papers_need = 400


# 函数区

# 将关键词分解为多个关键词
def splitKeywords(keywords):
    domain = []
    if keywords == '':
        return domain
    keywords = keywords.replace(' ', '')
    domain = keywords.split(';')
    return domain


# 将机构分解为多个机构
def institute2list(institute):
    institute = institute.replace(' ', '')
    institutes = []
    if not ('0' <= institute[0] <= '9'):
        institutes.append(institute)
        return institutes
    i, j = 0, 0
    while (i < len(institute)):
        while (institute[i] != '.'):
            i += 1
        j = i + 1
        while j < len(institute) and (not ('0' <= institute[j] <= '9')):
            j += 1
        institutes.append(institute[i + 1:j])
        i = j
    for item in range(len(institutes)):
        if ("知识工程" in institutes[item]) or ("符号计算" in institutes[item]):
            institutes[item] = "吉林大学符号计算与知识工程教育部重点实验室"
    return institutes


# 连接Neo4j
# 连接成功返回图谱句柄 连接失败返回空对象
def connectNeo4j():
    try:
        graph = Graph('bolt://localhost:7687', auth=('neo4j', '123456'))
        graph.delete_all()
        return graph
    except:
        return None


# 配置驱动
# 配置成功返回驱动器句柄 配置失败返回空对象
def createDriver():
    try:
        # 设置驱动器的环境
        options = webdriver.ChromeOptions()
        # 设置chrome不加载图片，提高速度
        options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        # 设置不显示窗口
        options.add_argument('--headless')
        driver = webdriver.Chrome(executable_path="D:/下载/chromedriver103.exe", options=options)
        driver.get("https://kns.cnki.net/kns8/AdvSearch")
        return driver
    except:
        return None


# 获取基本信息
def getBasicInf(driver, term):
    title_xpath = '''//*[@id="gridTable"]/table/tbody/tr[''' + str(term) + ''']/td[2]'''
    author_xpath = '''//*[@id="gridTable"]/table/tbody/tr[''' + str(term) + ''']/td[3]'''
    source_xpath = '''//*[@id="gridTable"]/table/tbody/tr[''' + str(term) + ''']/td[4]'''
    date_xpath = '''//*[@id="gridTable"]/table/tbody/tr[''' + str(term) + ''']/td[5]'''
    database_xpath = '''//*[@id="gridTable"]/table/tbody/tr[''' + str(term) + ''']/td[6]'''
    title = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, title_xpath))).text
    authors = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, author_xpath))).text
    source = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, source_xpath))).text
    date = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, date_xpath))).text
    database = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, database_xpath))).text
    return title, authors, source, date, database


# 获取作者机构
def getInstitution(driver):
    institute = WebDriverWait(driver, 30).until(EC.presence_of_element_located(
        (By.XPATH, "/html[1]/body[1]/div[2]/div[1]/div[3]/div[1]/div[1]/div[3]/div[1]/h3[2]"))).text
    instu = institute2list(institute)
    return instu


# 获取摘要
def getAbstract(driver):
    abstract = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CLASS_NAME, "abstract-text"))
    ).text
    return abstract


# 获取基金列表
# 参数：驱动 返回值：基金列表
def getFunds(driver):
    fund = []
    try:
        funds = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "funds"))
        ).text[:-1]
        funds = funds.replace(' ', '')
        fund = funds.split('；')
    except:
        fund = []
    finally:
        return fund


# 获取关键词
def getDomain(driver):
    try:
        keywords = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "keywords"))).text[:-1]
    except:
        keywords = ''
    domain = splitKeywords(keywords)
    return domain


# 匹配作者与机构
def matchAuthor2Institution(driver, au, instu, au2institution):
    for i in range(len(au)):
        sup = []
        try:
            sup = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                (By.XPATH, '''//*[@id="authorpart"]/span[''' + str(i + 1) + ''']/a/sup'''))).text
            sup = sup.split(',')
        except:
            sup = [1]
        finally:
            for item in sup:
                value = (au[i], instu[int(item) - 1])
                au2institution.append(value)
                Au2Institution.append(value)


# 匹配论文与机构
def matchPap2Institution(title, instu, pap2institution):
    for instut in instu:
        value = (title, instut)
        pap2institution.append(value)
        Pap2Institution.append(value)


# 匹配论文与作者
def matchPaper2Author(au, title, pap2au):
    for author in au:
        value = (title, author)
        pap2au.append(value)
        Pap2Au.append(value)


# 爬取引文：只有一种类型
def getCite_1(driver, cite):
    kind = driver.find_element_by_xpath('/html/body/div/div').text.split(' ')[0]
    if kind not in Legal_list:
        print(kind + "不属于爬取范围")
        return
    try:
        driver.find_element_by_xpath('html/body/div/div[2]')
        hasPageBar = True
    except:
        hasPageBar = False
    if not hasPageBar:
        ul = driver.find_element_by_xpath('/html/body/div/ul')
        papList = ul.find_elements_by_xpath('li')
        for pap in papList:
            try:
                papname = pap.find_element_by_xpath('a')
                cite.append(papname.text)
            except:
                papname = pap.text
                papname = papname.replace(']',';')
                papname = (papname.split(';'))[1]
                papname = papname[1:-2]
                cite.append(papname)
    else:
        sum_Papers = driver.find_element_by_xpath('/html/body/div[1]/div/b').find_element_by_xpath('span').text
        all = int((int(sum_Papers) - 1) / 10 + 1)
        for ii in range(all):
            driver.find_element_by_xpath('/html/body/div/div[2]/span/a[' + str(ii + 1) + ']').send_keys(Keys.ENTER)
            time.sleep(2)
            ul = driver.find_element_by_xpath('/html/body/div/ul')
            papList = ul.find_elements_by_xpath('li')
            for pap in papList:
                try:
                    papname = pap.find_element_by_xpath('a')
                    cite.append(papname.text)
                except:
                    papname = pap.text
                    papname = papname.replace(']', ';')
                    papname = (papname.split(';'))[1]
                    papname = papname[1:-2]
                    cite.append(papname)
            driver.find_element_by_xpath('/html/body/div/div[2]/span/a[1]').send_keys(Keys.ENTER)
            time.sleep(2)


# 爬取引文：有多种文章类型
def getCite_many(driver, cite, sumOfBox):
    for item in range(sumOfBox):
        kind = driver.find_element_by_xpath('html/body/div[' + str(item + 1) + ']/div').text.split(' ')[0]
        if kind not in Legal_list:
            print(kind + '不属于爬取范围')
            continue
        try:
            driver.find_element_by_xpath('html/body/div[' + str(item + 1) + ']/div[2]')
            hasPageBar = True
        except:
            hasPageBar = False
        if not hasPageBar:
            ul = driver.find_element_by_xpath('/html/body/div[' + str(item + 1) + ']/ul')
            papList = ul.find_elements_by_xpath('li')
            for pap in papList:
                try:
                    papname = pap.find_element_by_xpath('a')
                    cite.append(papname.text)
                except:
                    papname = pap.text
                    papname = papname.replace(']', ';')
                    papname = (papname.split(';'))[1]
                    papname = papname[1:-2]
                    cite.append(papname)
        else:
            sP = driver.find_element_by_xpath('/html/body/div[' + str(item + 1) + ']/div[1]/b').find_element_by_xpath(
                'span')
            sum_Papers = int(sP.text)
            all = int((sum_Papers - 1) / 10 + 1)
            for ii in range(all):
                driver.find_element_by_xpath(
                    '/html/body/div[' + str(item + 1) + ']/div[2]/span/a[' + str(ii + 1) + ']').send_keys(Keys.ENTER)
                time.sleep(2)
                ul = driver.find_element_by_xpath('/html/body/div[' + str(item + 1) + ']/ul')
                papList = ul.find_elements_by_xpath('li')
                for pap in papList:
                    try:
                        papname = pap.find_element_by_xpath('a')
                        cite.append(papname.text)
                    except:
                        papname = pap.text
                        papname = papname.replace(']', ';')
                        papname = (papname.split(';'))[1]
                        papname = papname[1:-2]
                        cite.append(papname)
                driver.find_element_by_xpath('/html/body/div[' + str(item + 1) + ']/div[2]/span/a[1]').send_keys(
                    Keys.ENTER)
                time.sleep(2)


# 处理文章标题
def washTitle(title):
    title = title.replace(' ', '')
    str = title[-4:]
    if str == "网络首发":
        title = title[:-4]
    return title


# 创建节点
def makeNodes(graph, au, instu, nodes):
    for item in instu:
        if nodes.match('Institution', name=item).first() is None:
            Inst = Node('Institution', name=item)
            graph.create(Inst)
    for item in au:
        if nodes.match('Author', name=item).first() is None:
            Author = Node('Author', name=item)
            graph.create(Author)


# 创建关系
def makeRelations(graph, pap2au, au2institution, pap2institution, nodes):
    for item in pap2au:
        p = nodes.match('Paper', title=item[0]).first()
        for Author in item[1]:
            au = nodes.match('Author', name=Author).first()
            rel = Relationship(p, "author is", au)
            graph.create(rel)
    for item in au2institution:
        au = nodes.match('Author', name=item[0]).first()
        inst = nodes.match('Institution', name=item[1]).first()
        rel = Relationship(au, 'work in', inst)
        graph.create(rel)
    for item in pap2institution:
        p = nodes.match('Paper', title=item[0]).first()
        inst = nodes.match('Institution', name=item[1]).first()
        rel = Relationship(p, 'function is', inst)
        graph.create(rel)


# 创建知识图谱
def makeGraph(graph, pap, au, instu, pap2au, au2institution, pap2institution):
    graph.create(pap)
    nodes = NodeMatcher(graph)
    for item in instu:
        if nodes.match('Institution', name=item).first() is None:
            Inst = Node('Institution', name=item)
            graph.create(Inst)
    for item in au:
        if nodes.match('Author', name=item).first() is None:
            Author = Node('Author', name=item)
            graph.create(Author)
    # 添加关系
    for item in pap2au:
        p = nodes.match('Paper', title=item[0]).first()
        au = nodes.match('Author', name=item[1]).first()
        rel = Relationship(p, "author is", au)
        graph.create(rel)
    for item in au2institution:
        au = nodes.match('Author', name=item[0]).first()
        inst = nodes.match('Institution', name=item[1]).first()
        rel = Relationship(au, 'work in', inst)
        graph.create(rel)
    for item in pap2institution:
        p = nodes.match('Paper', title=item[0]).first()
        inst = nodes.match('Institution', name=item[1]).first()
        rel = Relationship(p, 'function is', inst)
        graph.create(rel)


# 存储论文-机构关系
def pap_instu_Store(db):
    cur = db.cursor()
    cur.execute("DROP TABLE IF EXISTS paper2institution")
    sql = "create table paper2institution(paperName varchar(30), institution_name varchar(30))"
    cur.execute(sql)
    print("建表成功")
    SQLquery = "insert into paper2institution values (%s,%s)"
    for p2i in enumerate(Pap2Institution):
        pai = p2i[1]
        paperName = pai[0]
        institutionName = pai[1]
        value = (paperName, institutionName)
        try:
            cur.execute(SQLquery, value)
            db.commit()
        except pymysql.Error as e:
            print("本条插入失败")
            print(e)
            db.rollback()


# 存储论文-作者关系
def pap_au_Store(db):
    cur = db.cursor()
    cur.execute("DROP TABLE IF EXISTS paper2au")
    sql = "create table paper2au(paperName varchar(30), author_name varchar(10))"
    cur.execute(sql)
    print("建表成功!")
    SQLquery = "insert into paper2au values (%s,%s)"
    for p2a in enumerate(Pap2Au):
        pau = p2a[1]
        paper_name = pau[0]
        author = pau[1]
        value = (paper_name, author)
        try:
            cur.execute(SQLquery, value)
            db.commit()
        except pymysql.Error as e:
            print("本条数据插入失败")
            print(e)
            db.rollback()


# 存储作者-机构关系
def au_instu_Store(db):
    cur = db.cursor()
    cur.execute("DROP TABLE IF EXISTS au2institution")
    sql = "create table au2institution(author_Name varchar(10), institution_name varchar(30))"
    cur.execute(sql)
    print("建表成功!")
    SQLquery = "insert into au2institution values (%s,%s)"
    for a2i in enumerate(Au2Institution):
        aai = a2i[1]
        author_name = aai[0]
        institute = aai[1]
        value = (author_name, institute)
        try:
            cur.execute(SQLquery, value)
            db.commit()
        except pymysql.Error as e:
            print("本条数据插入失败")
            print(e)
            db.rollback()


# 主函数
if __name__ == "__main__":
    graph = Graph('bolt://localhost:7687', auth=('neo4j', 'myf021105'))
    graph.delete_all()
    driver = createDriver()
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '''/html/body/div[2]/div/div[2]/ul/li[4]'''))
    ).click()
    time.sleep(2)
    query = "AF=吉林大学软件学院 OR AF=吉林大学计算机科学与技术学院"
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '''/html/body/div[2]/div/div[2]/div/div[1]/div[1]/div[2]/textarea'''))
    ).send_keys(query)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, '''/html/body/div[2]/div/div[2]/div/div[1]/div[1]/div[2]/div[2]/input'''))
    ).click()
    res_num = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '''//*[@id="countPageDiv"]/span[1]/em'''))
    ).text
    res_num = int(res_num.replace(',', ''))
    page_num = int(res_num / 20) + 1
    print(f"共找到{res_num}条结果，{page_num}页")
    # papers_need = res_num
    count = 0
    while count < papers_need:
        time.sleep(1)
        title_list = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "fz14")))
        for i in range(len(title_list)):
            pap2au = []
            au2institution = []
            pap2institution = []
            term = i + 1
            time.sleep(0.5)
            try:
                title, authors, source, date, database = getBasicInf(driver, term)
                title = washTitle(title)
                title_list[i].click()
                au = authors.replace(' ', '').split(';')
                n = driver.window_handles
                driver.switch_to_window(n[-1])
                fund = getFunds(driver)
                domain = getDomain(driver)
                abstract = getAbstract(driver)
                instu = getInstitution(driver)
                matchAuthor2Institution(driver=driver, au=au, instu=instu, au2institution=au2institution)
                matchPap2Institution(title=title, instu=instu, pap2institution=pap2institution)
                matchPaper2Author(au=au, title=title, pap2au=pap2au)
                print("基本信息爬取完毕")
                print(title)
                print(au)
                print(instu)
                print(domain)
                print("开始爬取引文")
                cite = []
                driver.switch_to_frame("frame1")
                time.sleep(3)
                Boxs = driver.find_elements_by_class_name("essayBox")
                sumOfbox = Boxs.__len__()
                if sumOfbox == 1:
                    getCite_1(driver=driver, cite=cite)
                else:
                    getCite_many(driver=driver, cite=cite, sumOfBox=sumOfbox)

                print(len(cite))
                print(cite)
                print("---------------------------------------------------")
                print("-------------------开始构建知识图谱-------------------")
                pap = Node('Paper', title=title, abstract=abstract, source=source, funds=fund, cite_papers=cite, domain=domain)
                makeGraph(graph=graph, pap=pap, au=au, instu=instu, pap2au=pap2au, pap2institution=pap2institution, au2institution=au2institution)
                driver.switch_to_default_content()
            except:
                print(f"第{count + 1}条爬取失败")
                continue
            finally:
                n2 = driver.window_handles
                if len(n2) > 1:
                    driver.close()
                    driver.switch_to_window(n2[0])
                # 计数,判断需求是否足够
                count += 1
                if count >= papers_need:
                    break
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//a[@id='PageNext']"))).click()

    driver.close()
    print("------------------开始存储到MySQL------------------")
    try:
        db = pymysql.connect(user=DBUSER, password=DBPASS, host=DBHOST, database=DBNAME)
        au_instu_Store(db=db)
        pap_instu_Store(db=db)
        pap_au_Store(db=db)
    except pymysql.Error as e:
        print("数据库连接失败，原因如下")
        print(e)

    print("End")
