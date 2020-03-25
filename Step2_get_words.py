# coding=utf-8
# 选择属性/特性
import spacy
from hearstPatterns.hearstPatterns import HearstPatterns
import pymysql

nlp=spacy.load('en_coref_lg')
hearst = HearstPatterns(extended=True)
INVALIDNOUN=set()
INVALIDADJ=set()

# 1.根据给定句式找到NOUN/ADJ
def get_noun_adj():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()

    fout=open("relation1_1","w",encoding='utf-8')

    sql="SELECT api_id,qualified_name,clean_text FROM jdk_api_valid WHERE api_type not in(6,12,14)"
    cursor.execute(sql)
    index=0
    for res in cursor.fetchall():
        index+=1
        id=res[0]
        qualified_name=res[1]
        alias=get_alias(qualified_name)
        clean_text=res[2]
        has_a = set()
        is_a = set()
        related_to = set()
        adj=set()
        clean_text=nlp(clean_text)
        for sent in list(clean_text.sents):
            has_a1, is_a1, related_to1,adj1 = str_match1(qualified_name, sent)
            has_a, is_a, related_to,adj = batch_union4(has_a, is_a, related_to,adj, has_a1, is_a1, related_to1,adj1)
            adj1=find_adj(sent,alias)
            adj=adj.union(adj1)
        alias=get_alias(qualified_name)
        has_a=delete_invalid_noun(has_a,alias)
        is_a = delete_invalid_noun(is_a, alias)
        related_to=delete_invalid_noun(related_to,alias)

        if has_a or is_a or related_to:
            fout.write(str(id)+"\t")
            if adj:
                for a in adj:
                    fout.write(a+"\t")
            fout.write("\n")

            write_set_in_file(qualified_name, has_a, fout, "has_a")
            write_set_in_file(qualified_name, is_a, fout, "is_a")
            write_set_in_file(qualified_name, related_to, fout, "related_to")
            fout.write("\n")
            print("1.num:%d\tid:%d"%(index,id))
    fout.close()
    cursor.close()
    db.close()


#2.Field/Constant的full_declaration最后一个单词/Parameter名字的最后一个单词也是属于API的属性,并且这些属性的adj也是API的特性
def get_more_attribute():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    fout = open("relation1_2", "w", encoding='utf-8')
    sql="SELECT qualified_name,clean_text FROM jdk_api_valid WHERE api_type in(6,12)"
    cursor.execute(sql)
    num=0
    for res in cursor.fetchall():
        num+=1
        api_name=".".join(res[0].split(".")[:-1])
        alias=get_alias(api_name)
        alias.add(res[0])
        attribute=res[0].split(".")[-1]
        clean_text=nlp(res[1])
        adj=set()
        for sent in list(clean_text.sents):
            adj=adj.union(find_adj(sent,alias))
        sql="SELECT api_id FROM jdk_api_valid WHERE qualified_name=%s"
        cursor.execute(sql,(api_name))
        for res1 in cursor.fetchall():
            api_id=res1[0]
            fout.write(str(api_id) + "\t")
            if adj:
                for a in adj:
                    fout.write(a + "\t")
            fout.write("\n")
            fout.write(api_name+" has_a "+attribute+"\n\n")
        print("2.1.num:%d"%num)

    sql="SELECT api_id,qualified_name,clean_text FROM jdk_api_valid WHERE api_type=14"
    cursor.execute(sql)
    for res in cursor.fetchall():
        id=res[0]
        attribute=res[1].split()[-1]
        clean_text=res[2]
        if clean_text:
            clean_text=nlp(clean_text)
        sql="SELECT api_id,qualified_name FROM jdk_api_valid WHERE api_id in (SELECT start_api_id FROM java_api_relation WHERE end_api_id=%s and relation_type=7)"
        cursor.execute(sql,(id))
        for res in cursor.fetchall():
            num+=1
            api_id=res[0]
            api_name=res[1]
            alias = get_alias(api_name)
            alias.add(res[0])
            adj = set()
            if clean_text:
                for sent in list(clean_text.sents):
                    adj = adj.union(find_adj(sent, alias))
            fout.write(str(api_id) + "\t")
            if adj:
                for a in adj:
                    fout.write(a + "\t")
            fout.write("\n")
            fout.write(api_name + " has_a " + attribute + "\n\n")
            print("2.2.num:%d" % num)

    fout.close()
    cursor.close()
    db.close()



#3.得到文档里每个名词(原型)/形容词出现次数，从频率高的筛选无效词
def get_noun_adj_num():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    dict_noun_num=dict()
    dict_adj_num=dict()

    fout1 = open("all_noun_num", "w", encoding='utf-8')
    fout2 = open("all_adj_num", "w", encoding='utf-8')

    sql="SELECT api_id,qualified_name,clean_text FROM jdk_api_valid"
    cursor.execute(sql)
    index=0
    for res in cursor.fetchall():
        index+=1
        api_id=res[0]
        qualified_name=res[1]
        clean_text=res[2]
        if clean_text:
            clean_text=nlp(clean_text)
            for token in clean_text:
                if token.pos_=="NOUN" and token.text!=qualified_name:
                    num=dict_noun_num.get(token.lemma_,0)+1
                    dict_noun_num[token.lemma_]=num
                elif token.pos_=="ADJ":
                    num = dict_adj_num.get(token.lemma_, 0) + 1
                    dict_adj_num[token.lemma_] = num
        print("num:%d\tid:%d"%(index,api_id))
    dict_noun_num = sorted(dict_noun_num.items(),key = lambda x:x[1],reverse = True)
    dict_adj_num = sorted(dict_adj_num.items(),key = lambda x:x[1],reverse = True)

    for (noun,num) in dict_noun_num:
        fout1.write(noun+":"+str(num)+"\n")
    for (adj,num) in dict_adj_num:
        fout2.write(adj+":"+str(num)+"\n")
    fout1.close()
    fout2.close()
    cursor.close()
    db.close()


#4.删除all_noun_num/all_adj_num中明显无效的词
def delete_noun_adj():
    fin=open("all_noun_num","r",encoding='utf-8')
    fout=open("invalid_noun_num1","w")
    all=fin.readlines()
    index=0
    for line in all:
        index+=1
        if line.startswith("java") or line.startswith("Java") or ('(' in line):
            continue
        else:
            num=int(line.split(":")[1][:-1])
            if num>300:
                fout.write(line)
            else:
                break
        print(index)
    fin.close()
    fout.close()

    fin = open("all_adj_num", "r", encoding='utf-8')
    fout = open("invalid_adj_num1", "w")
    all = fin.readlines()
    index = 0
    for line in all:
        index += 1
        adj=line.split(":")[0]
        nlp_adj=nlp(adj)
        token=nlp_adj[0]
        if token.pos_!="ADJ":
            continue
        if adj.startswith("java") or \
                adj.startswith("Java") or \
                ('(' in adj) or(')'in adj)\
                or(adj[0]=="-")or(adj[-1]=="-"):
            continue
        else:
            num = int(line.split(":")[1][:-1])
            if num > 50:
                fout.write(line)
            else:
                break
        print(index)
    fin.close()
    fout.close()




#5.删除无效属性
def delete_invalid_attribute(file_in,file_out):
    fin=open("invalid_noun_num2","r")
    all=fin.readlines()
    for line in all:
        tmp_noun=line.split(":")[0]
        INVALIDNOUN.add(tmp_noun)
    fin.close()
    fin = open("invalid_adj_num2", "r")
    all = fin.readlines()
    for line in all:
        tmp_adj = line.split(":")[0]
        INVALIDADJ.add(tmp_adj)
    fin.close()
    fin=open(file_in,"r")
    fout=open(file_out,"w")
    all=fin.readlines()
    index=0
    while index<len(all):
        if all[index][0].isdigit():
            tmp=all[index][:-1].split("\t")
            id=tmp[0]
            adj=set()
            if len(tmp)>1:
                for a in tmp[1:]:
                    if a and a not in INVALIDADJ:
                        adj.add(a)
            relation=set()
            index+=1
            while all[index]!="\n" and (not all[index][0].isdigit()):
                print(index)
                attribute=all[index][:-1].split(" ")[2]
                if attribute not in INVALIDNOUN:
                    relation.add(all[index])
                index+=1
            if relation or adj:
                fout.write(id+"\t")
                for a in adj:
                    fout.write(a+"\t")
                fout.write("\n")
            for rel in relation:
                fout.write(rel)
            fout.write("\n")
        index+=1
    fin.close()
    fout.close()



#6.将relation的同id的关系合并
def merge_relation():
    fin1=open("relation2_1","r")
    fin2=open("relation2_2","r")

    fout=open("relation3","w")
    dict_relation=dict()
    dict_adj=dict()
    all=fin1.readlines()+fin2.readlines()
    index = 0
    while index < len(all):
        if all[index][0].isdigit():
            tmp=all[index].split("\t")
            id = int(tmp[0])
            adj=set()
            if len(tmp)>1:
                for a in tmp[1:-1]:
                    adj.add(a)
            relation = set()
            index += 1
            while all[index] != "\n" and (not all[index][:-1].isdigit()):
                print(index)
                relation.add(all[index][:-1])
                index += 1
            relation_set=dict_relation.get(id,set()).union(relation)
            adj_set=dict_adj.get(id,set()).union(adj)
            dict_relation[id]=relation_set
            dict_adj[id]=adj_set
        index+=1
    for id in range(1,int(max(dict_relation.keys()))+1):
        relation = dict_relation.get(id)
        adj=dict_adj.get(id)
        if relation or adj:
            fout.write(str(id) + "\t")
            for a in adj:
                fout.write(a+"\t")
            fout.write("\n")
            for r in relation:
                fout.write(r + "\n")
            fout.write("\n")

    fin1.close()
    fin2.close()
    fout.close()



# help.句式匹配
def str_match1(qualified_name,sent):
    line=[]
    line_tags=[]
    for word in sent:
        line.append(word.text)
        line_tags.append(word.pos_)
    pattern0=[qualified_name,'provide']#API provide[s] [N1]  API has N1
    pattern1=[qualified_name,'provide','for']#API provide[s] [N1] for [N2]    API has N1
    pattern2=[qualified_name,'provide','with']#API provide[s] [N1] with [N2]    API has N2
    pattern3=[qualified_name,'contain']#API contain[s] N1    API has N1
    pattern4=[qualified_name,'is']#API is N1    API is N1
    pattern5 = [qualified_name, 'has']  # API has N1    API has N1
    pattern6=[qualified_name,"define","for"]#API define[s] N1 for N2    API has N1
    pattern7=[qualified_name,"define"]#API define[s] [N1]    API has N1
    pattern8=[qualified_name+"'s"]#API's N    API has N
    has_a = set()
    is_a = set()
    related_to = set()
    adj=set()
    indexs0=match(pattern0,line)
    indexs1=match(pattern1,line)
    indexs2 = match(pattern2, line)
    indexs3 = match(pattern3, line)
    indexs4 = match(pattern4, line)
    indexs5 = match(pattern5, line)
    indexs6 = match(pattern6, line)
    indexs7 = match(pattern7, line)
    indexs8=match(pattern8,line)

    if indexs0 and "NOUN" in line_tags[indexs0[1]:]:
        tmpindex = line_tags[indexs0[1]:].index("NOUN") + indexs0[1]
        has_a.add(sent[tmpindex].lemma_)
        adj=adj.union(find_adj(sent, {sent[tmpindex].text}))
        if "and" in line[indexs0[1]:]:
            tmpindex = line[indexs0[1]:].index("and")+ indexs0[1]
            if "NOUN" in line_tags[tmpindex:]:
                tmpindex = line_tags[tmpindex:].index("NOUN") + tmpindex
                has_a.add(sent[tmpindex].lemma_)
                adj = adj.union(find_adj(sent, {sent[tmpindex].text}))
    if indexs1 and "NOUN" in line_tags[indexs1[1]:indexs1[2]]:
        tmpindex=line_tags[indexs1[1]:indexs1[2]].index("NOUN")+indexs1[1]
        has_a.add(sent[tmpindex].lemma_)
        adj=adj.union(find_adj(sent, {sent[tmpindex].text}))
    if indexs2 and "NOUN" in line_tags[indexs2[2]:]:
        tmpindex = line_tags[indexs2[2]:].index("NOUN")+indexs2[2]
        has_a.add(sent[tmpindex].lemma_)
        adj=adj.union(find_adj(sent, {sent[tmpindex].text}))
    if indexs3 and "NOUN" in line_tags[indexs3[1]:]:
        tmpindex = line_tags[indexs3[1]:].index("NOUN") + indexs3[1]
        has_a.add(sent[tmpindex].lemma_)
        adj=adj.union(find_adj(sent, {sent[tmpindex].text}))
        if "and" in line[indexs3[1]:]:
            tmpindex=line[indexs3[1]:].index("and")+ indexs3[1]
            if "NOUN" in line_tags[tmpindex:]:
                tmpindex = line_tags[tmpindex:].index("NOUN")+tmpindex
                has_a.add(sent[tmpindex].lemma_)
                adj = adj.union(find_adj(sent, {sent[tmpindex].text}))
    if indexs4 and "NOUN" in line_tags[indexs4[1]:]:
        tmpindex = line_tags[indexs4[1]:].index("NOUN") + indexs4[1]
        is_a.add(sent[tmpindex].lemma_)
        adj=adj.union(find_adj(sent, {sent[tmpindex].text}))
        if "and" in line[indexs4[1]:]:
            tmpindex = line[indexs4[1]:].index("and")+ indexs4[1]
            if "NOUN" in line_tags[tmpindex:]:
                tmpindex = line_tags[tmpindex:].index("NOUN") + tmpindex
                is_a.add(sent[tmpindex].lemma_)
                adj = adj.union(find_adj(sent, {sent[tmpindex].text}))
    if indexs5 and "NOUN" in line_tags[indexs5[1]:]:
        tmpindex = line_tags[indexs5[1]:].index("NOUN") + indexs5[1]
        has_a.add(sent[tmpindex].lemma_)
        adj=adj.union(find_adj(sent, {sent[tmpindex].text}))
        if "and" in line[indexs5[1]:]:
            tmpindex = line[indexs5[1]:].index("and")+ indexs5[1]
            if "NOUN" in line_tags[tmpindex:]:
                tmpindex = line_tags[tmpindex:].index("NOUN") + tmpindex
                has_a.add(sent[tmpindex].lemma_)
                adj = adj.union(find_adj(sent, {sent[tmpindex].text}))
    if indexs6 and "NOUN" in line_tags[indexs6[1]:indexs6[2]]:
        tmpindex=line_tags[indexs6[1]:indexs6[2]].index("NOUN")+indexs6[1]
        has_a.add(sent[tmpindex].lemma_)
        adj=adj.union(find_adj(sent, {sent[tmpindex].text}))
    if indexs7 and "NOUN" in line_tags[indexs7[1]:]:
        tmpindex = line_tags[indexs7[1]:].index("NOUN") + indexs7[1]
        has_a.add(sent[tmpindex].lemma_)
        adj=adj.union(find_adj(sent, {sent[tmpindex].text}))
        if "and" in line[indexs7[1]:]:
            tmpindex = line[indexs7[1]:].index("and")+ indexs7[1]
            if "NOUN" in line_tags[tmpindex:]:
                tmpindex = line_tags[tmpindex:].index("NOUN") + tmpindex
                has_a.add(sent[tmpindex].lemma_)
                adj = adj.union(find_adj(sent, {sent[tmpindex].text}))
    if indexs8 and "NOUN" in line_tags[indexs8[0]:]:
        tmpindex = line_tags[indexs8[0]:].index("NOUN") + indexs8[0]
        has_a.add(sent[tmpindex].lemma_)
        adj=adj.union(find_adj(sent, {sent[tmpindex].text}))


    has_a1,is_a1,adj1 = str_match2(sent, ["provide", "provides"], "has_a")
    has_a, is_a,adj=batch_union3(has_a, is_a,adj, has_a1, is_a1,adj1)

    has_a1, is_a1,adj1=str_match2(sent,["contain","contains"],"has_a")
    has_a, is_a,adj=batch_union3(has_a, is_a,adj, has_a1, is_a1,adj1)

    has_a1, is_a1,adj1=str_match2(sent,["is","are"],"is_a")
    has_a, is_a,adj=batch_union3(has_a, is_a,adj, has_a1, is_a1,adj1)

    has_a1, is_a1,adj1=str_match2(sent,["has","have"],"has_a")
    has_a, is_a,adj=batch_union3(has_a, is_a,adj, has_a1, is_a1,adj1)

    is_a1,adj1=hearstP(qualified_name,sent)
    is_a,adj=batch_union2(is_a,adj,is_a1,adj1)

    if (not has_a) and (not is_a):
        related_to=related(sent)

    return has_a,is_a,related_to,adj


# help.依存分析
def str_match2(sent, verb,relation):
    has_a = set()
    is_a = set()
    adj=set()
    for token in sent:
        if (token.dep_=="dobj" or token.dep_=="pobj") and (token.head.text in verb):
            if relation=="has_a":
                has_a.add(token.lemma_)
                adj = adj.union(find_adj(sent, {token.text}))
            elif relation=="is_a":
                is_a.add(token.lemma_)
                adj = adj.union(find_adj(sent,{token.text}))
    return has_a,is_a,adj


# help.pattern是诸如[qualified_name,'provide','for']的模式，在line中匹配每个元素的位置
def match(pattern,line):
    indexs=[0]
    for p in pattern:
        k=indexs[-1]
        while k<len(line):
            if p in line[k]:
                indexs.append(k)
                break
            k+=1
        if k>=len(line):
            return []
    return indexs[1:]


# help.hearstpatterns得到is-a关系
def hearstP(qualified_name,sent):
    line = sent.text
    hyponyms = hearst.find_hyponyms(line)
    res=set()
    adj=set()
    for (s,g) in hyponyms:
        if s==qualified_name:
            g=nlp(s)
            g=g[0]
            res.add(g.lemma_)
            adj = adj.union(find_adj(sent, {g.text}))
    return res,adj


#help.找到句子中的名词
def related(sent):
    res=set()
    for token in sent:
        if token.tag_=="NOUN":
            res.add(token.lemma_)
    return res


#help.将属性写到文件
def write_set_in_file(qualified,set,file,relation):
    s=qualified+" "+relation+" "
    for line in set:
        file.write(s+line+"\n")


# help.批量合并集合
def batch_union2(has_a, is_a, has_a1, is_a1):
    if has_a1:
        has_a=has_a.union(has_a1)
    if is_a1:
        is_a=is_a.union(is_a1)
    return has_a,is_a


# help.批量合并集合
def batch_union3(has_a, is_a,relate_to, has_a1, is_a1,relate_to1):
    if has_a1:
        has_a=has_a.union(has_a1)
    if is_a1:
        is_a=is_a.union(is_a1)
    if relate_to1:
        relate_to=relate_to.union(relate_to1)
    return has_a,is_a,relate_to


# help.批量合并集合
def batch_union4(has_a, is_a,relate_to,adj, has_a1, is_a1,relate_to1,adj1):
    if has_a1:
        has_a=has_a.union(has_a1)
    if is_a1:
        is_a=is_a.union(is_a1)
    if relate_to1:
        relate_to=relate_to.union(relate_to1)
    if adj1:
        adj=adj.union(adj1)
    return has_a,is_a,relate_to,adj


# help.删除set中同时为API别名的词，并对每个词做词性分析，删除除了NOUN以外的词
def delete_invalid_noun(word_set,alias):
    inter=word_set.intersection(alias)
    word_set=word_set.difference(inter)
    res=set()
    for word in word_set:
        word=nlp(word)[0]
        if word.pos_=="NOUN":
            res.add(word.lemma_)
    return res




#help.得到一个限定名的所有别名
def get_alias(qualified_name):
    alias = set()
    alias.add(qualified_name)
    # 1.简写，取完全限定名最后一个单词
    name=qualified_name.split(".")[-1]
    alias.add(name)

    #2.如果是方法，不含参数和括号
    if name[-1]==")":
        alias.add(name.split("(")[0])

    #3.驼峰命名是标准，改成全小写或者_连接
    tmp = []
    for index, char in enumerate(name):
        if char.isupper() and index != 0:
            tmp.append("_")
        tmp.append(char)
    alias.add("".join(tmp).lower())
    alias.add(name.lower())

    return alias


#help.寻找adj,nouns中放的是adj修饰的名词
def find_adj(sent,nouns):
    adj=set()
    subject=""
    for token in sent:
        if token.dep_=="nsubj" or token.dep_=="nsubjpass":
            subject=token.text
        elif token.pos_=="ADJ" and token.dep_=="amod"  and token.head.text in nouns:
            adj.add(token.text)
        elif token.pos_=="ADJ" and token.dep_=="acomp"  and subject and subject in nouns:
            adj.add(token.text)
    return adj





if __name__=='__main__':
    #get_noun_adj()#√
    #get_more_attribute()#√
    #get_noun_adj_num()#√
    #delete_noun_adj()#√

    delete_invalid_attribute("relation1_1","relation2_1")#√
    delete_invalid_attribute("relation1_2","relation2_2")#√
    merge_relation()#√


