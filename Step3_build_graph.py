from py2neo import Node, Relationship, Graph
from py2neo.ogm import GraphObject, Property, RelatedTo, RelatedFrom
import pymysql


dict_api_type = {1:"package",2:"class",3:"interface",4:"class",5:"class",6:"field",7:"method",8:"class",9:"class",11:"method",12:"constant",14:"parameter"}
graph = Graph("http://localhost:7474", username="neo4j", password="123456")
dict_relation = {1:"BELONG_TO",2:"EXTENDS",3:"IMPLEMENTS"}


class API(GraphObject):
    __primarykey__ = 'name'
    name = Property()
    id = Property()
    classification = Property()#聚类分析用
    belong_to = RelatedTo("API")
    extends = RelatedTo("API")
    implements = RelatedTo("API")
    has_a = RelatedTo("Attribute")
    is_a=RelatedTo("Attribute")
    related_to=RelatedTo("Attribute")
    description_is=RelatedTo("Attribute")

    def __init__(self,name,id):
        self.name=name
        self.id=id

    def add_relation(self,relation_type,end_node_obj):
        if relation_type=="BELONG_TO":
            self.belong_to.add(end_node_obj)
        elif relation_type=="EXTENDS":
            self.extends.add(end_node_obj)
        elif relation_type=="IMPLEMENTS":
            self.implements.add(end_node_obj)
        elif relation_type=="has_a":
            self.has_a.add(end_node_obj)
        elif relation_type=="is_a":
            self.is_a.add(end_node_obj)
        elif relation_type == "related_to":
            self.related_to.add(end_node_obj)
        elif relation_type=="description_is":
            self.description_is.add(end_node_obj)


class Package(API):
    __primarykey__ = 'name'


class Class(API):
    __primarykey__ = 'name'


class Interface(API):
    __primarykey__ = 'name'


class Method(API):
    __primarykey__ = 'name'


class APIFactory():
    def createAPI(self,api_type,name,id):
        if api_type=="package":
            return Package(name,id)
        elif api_type=="interface":
            return Interface(name,id)
        elif api_type=="class":
            return Class(name,id)
        else:
            return Method(name,id)


class Attribute(GraphObject):
    __primarykey__ = 'description'
    description = Property()
    type = Property()#ADJ/NOUN
    classification = Property()#聚类分析分类

    def __init__(self,description,type):
        self.description=description
        self.type=type


# 1.创建API节点
def create_api_node():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    sql="SELECT api_id,qualified_name,api_type FROM jdk_api_valid WHERE api_type not in(6,12,14)"
    cursor.execute(sql)
    api_factory=APIFactory()
    for res in cursor.fetchall():
        api_id=res[0]
        qualified_name=res[1]
        api_type=dict_api_type[res[2]]
        api_obj = api_factory.createAPI(api_type,qualified_name,api_id)
        graph.push(api_obj)
    cursor.close()
    db.close()


# 2.创建API之间的关系,API：package/class/interface/method，关系：belongto/extends/implement
def create_api_relation():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    sql = "SELECT start_api_id,end_api_id,relation_type FROM java_api_relation WHERE relation_type in (1,2,3) and start_api_id in (SELECT api_id FROM jdk_api_valid WHERE api_type not in (6,12,14))"
    cursor.execute(sql)
    for rel in cursor.fetchall()[1:]:
        start_api_id=rel[0]
        end_api_id=rel[1]
        relation_type=dict_relation[rel[2]]
        start_api_obj=match_api_obj(start_api_id,cursor)
        end_api_obj=match_api_obj(end_api_id,cursor)
        start_api_obj.add_relation(relation_type,end_api_obj)
        graph.push(start_api_obj)
        print(start_api_id)
    cursor.close()
    db.close()


# 3.创建属性节点,以及API与属性之间的关系
def create_attribute_node():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    fin=open("relation3","r")
    all=fin.readlines()
    adjs = set()
    attrs = set()
    index=0
    while index<len(all):
        if all[index][0].isdigit():
            print(all[index])
            tmp = all[index][:-1].split("\t")
            id = int(tmp[0])
            api_obj = match_api_obj(id, cursor)
            if len(tmp) > 1:
                for a in tmp[1:]:
                    if a=='':
                        break
                    if a not in adjs:
                        adjs.add(a)
                        attr_obj=Attribute(a,"ADJ")
                        graph.push(attr_obj)
                    else:
                        attr_obj=Attribute.match(graph).where(description=a).first()
                    api_obj.add_relation("description_is",attr_obj)
            index += 1
            while all[index] != "\n" and (not all[index][0].isdigit()):
                print(all[index])
                a = all[index][:-1].split(" ")[2]
                if a not in attrs:
                    attrs.add(a)
                    attr_obj = Attribute(a, "NOUN")
                    graph.push(attr_obj)
                else:
                    attr_obj = Attribute.match(graph).where(description=a).first()
                relation = all[index][:-1].split(" ")[1]
                api_obj.add_relation(relation, attr_obj)
                index += 1
            graph.push(api_obj)

        index += 1
    cursor.close()
    db.close()


# help.根据id查询到API对象
def match_api_obj(api_id, cursor):
    sql="SELECT api_type FROM jdk_api_valid WHERE api_id=%d"%api_id
    cursor.execute(sql)
    api_type=dict_api_type[cursor.fetchall()[0][0]]
    if api_type=="package":
        return Package.match(graph).where(id=api_id).first()
    elif api_type=="interface":
        return Interface.match(graph).where(id=api_id).first()
    elif api_type=="class":
        return Class.match(graph).where(id=api_id).first()
    else:
        return Method.match(graph).where(id=api_id).first()


if __name__ == '__main__':
    # create_api_node()
    # create_api_relation
    create_attribute_node()
