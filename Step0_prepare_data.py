# coding=utf-8
# 数据准备

import pymysql
from bs4 import BeautifulSoup


#合并一个api的两个元组中的html 和clean_text
def read_data():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    sql = "SELECT distinct id FROM jdk_all_api_entity"
    cursor.execute(sql)
    api_ids = cursor.fetchall()
    for r in api_ids:
        id = r[0]
        sql = "SELECT  html,clean_text FROM java_api_html_text_clean where api_id=%d" % id
        cursor.execute(sql)
        res = cursor.fetchall()
        if len(res) == 2:
            html1=res[0][0]
            html2=res[1][0]
            clean1 = res[0][1]
            clean2 = res[1][1]
            html=merge_sentences(html1,html2)
            clean=merge_sentences(clean1,clean2)
        elif len(res)==1:
            html=res[0][0]
            clean=res[0][1]
        else:
            continue
        html=html.replace("'","''")
        clean=clean.replace("'","''")
        sql="insert into merge_api_html_text_clean(api_id, html, clean_text) value (%s,%s,%s)"
        cursor.execute(sql,(id,html,clean))
        db.commit()
        print(id)
    cursor.close()
    db.close()


#合并两个句子，剔除重复部分
def merge_sentences(s1,s2):
    if s1 in s2:
        return s2
    else:
        if s1.endswith("."):
            return s1+" "+s2
        else:
            return s1+". "+s2


#给short_description去标签
def modified_data1():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()

    sql = "SELECT distinct id FROM jdk_all_api_entity where id<7578"
    cursor.execute(sql)
    api_ids = cursor.fetchall()
    for r in api_ids:
        id=r[0]
        sql = "SELECT short_description FROM jdk_all_api_entity where id=%d"%id
        cursor.execute(sql)
        description = cursor.fetchall()[0][0]
        if description:
            description = BeautifulSoup(description, 'html.parser').get_text()
            sql="update jdk_all_api_entity set short_description=%s where id=%s"
            cursor.execute(sql,(description,id))
            db.commit()
            print(id)
    cursor.close()
    db.close()


#删除clean_text中连续的两个''中的一个
def modified_data2():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()

    sql = "SELECT api_id,clean_text FROM merge_api_html_text_clean"
    cursor.execute(sql)
    res = cursor.fetchall()
    for r in res:
        api_id=r[0]
        clean_text=r[1]
        clean_text=clean_text.replace("''","'")
        sql="update merge_api_html_text_clean set clean_text=%s where api_id=%s"
        cursor.execute(sql,(clean_text,api_id))
        db.commit()
        print(api_id)
    cursor.close()
    db.close()


def delete_blank():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    sql = "SELECT id,short_description FROM jdk_all_api_entity where id in()"
    cursor.execute(sql)
    res = cursor.fetchall()
    for r in res:
        api_id=r[0]
        short_description=r[1]
        if short_description:
            short_description=' '.join(short_description.split())
            sql="UPDATE jdk_all_api_entity SET short_description=%s WHERE id=%s"
            cursor.execute(sql,(short_description,api_id))
            db.commit()
            print(api_id)
    cursor.close()
    db.close()


#生成一个全新的表，只有有效的元组
def merge_table():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    sql = "SELECT id,api_type,qualified_name,short_description FROM jdk_all_api_entity where api_type not in (13,15,16)"
    cursor.execute(sql)
    res = cursor.fetchall()
    for r in res:
        api_id=r[0]
        api_type=r[1]
        qualified_name=r[2]
        short_description=r[3]
        sql="SELECT clean_text FROM merge_api_html_text_clean where api_id=%s"
        cursor.execute(sql,api_id)
        clean_text=cursor.fetchall()
        if clean_text:
            clean_text=clean_text[0][0]
        else:
            clean_text=short_description
        sql="INSERT INTO jdk_api_valid (api_id, api_type, qualified_name,clean_text) VALUE (%s,%s,%s,%s)"
        cursor.execute(sql,(api_id,api_type,qualified_name,clean_text))
        print(api_id)
    db.commit()
    cursor.close()
    db.close()


#删除clean_text中的full_declaration
def delete_name():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    sql = "SELECT a.id,a.full_declaration,b.clean_text FROM jdk_all_api_entity as a,merge_api_html_text_clean as b where a.id=b.api_id"
    cursor.execute(sql)
    res = cursor.fetchall()
    for r in res:
        api_id=r[0]
        full_declaration=r[1]
        clean_text=r[2]
        if full_declaration and clean_text and full_declaration in clean_text:
            clean_text=clean_text.replace(full_declaration,'')
            for index in range(len(clean_text)):
                if clean_text[index].isalpha():
                    clean_text = clean_text[index:]
                    break
            sql='UPDATE merge_api_html_text_clean SET clean_text=%s where api_id=%s'
            cursor.execute(sql,(clean_text,api_id))
            db.commit()
            print(api_id)
    cursor.close()
    db.close()


#删除有问题的clean_text中的标签
def modified_clean():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()

    fo=open("tmp","r")
    all=fo.readlines()
    for line in all:
        id=line.split(' ')[0]
        sql = "SELECT api_id,clean_text FROM merge_api_html_text_clean where api_id=%s"
        cursor.execute(sql,id)
        res = cursor.fetchall()
        for r in res:
            api_id = r[0]
            clean_text = r[1]
            if clean_text:
                clean_text = BeautifulSoup(clean_text, 'html.parser').get_text()
                sql = 'UPDATE merge_api_html_text_clean SET clean_text=%s where api_id=%s'
                cursor.execute(sql,(clean_text,api_id))
                db.commit()
                print(api_id)
    cursor.close()
    db.close()



def judge():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()

    sql = "SELECT id,short_description FROM jdk_all_api_entity"
    cursor.execute(sql)
    res = cursor.fetchall()
    for r in res:
        api_id = r[0]
        description = r[1]
        sql="SELECT clean_text FROM merge_api_html_text_clean where api_id=%s"
        cursor.execute(sql,api_id)
        db.commit()
        clean=cursor.fetchall()
        if clean:
            clean=clean[0][0]
            if description and not description in clean:
                print(api_id,"not ok")



if __name__ == '__main__':
    #modified_data1()
    #judge()
    merge_table()