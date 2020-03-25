# coding=utf-8
# 预处理数据
import spacy
import pymysql
import string


nlp=spacy.load('en_coref_lg')
NOUN={"NOUN","PRON","PROPN"}#表示名词的标记
VERB={"VERB","AUX"}#表示动词的标记
IGNORE={"DET","INTJ","NUM","PART","SYM","X","SPACE"}#表示可忽略词的标记
BE={"am","Am","is","Is","was","Was","are","Are","were","Were"}
APITYPE={"class","package","method","interface"}
dict_api_type={1:"package",2:"class",3:"interface",4:"class",5:"class",6:"field",7:"method",8:"class",9:"class",11:"method",12:"constant"}
DET={"the","The","this","This"}#表示确定限定词
all_alias=dict()


#1.提及替换:指代消解；物主代词加's；the class替换
def data_coref_resolved():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    sql = "select api_id,api_type,qualified_name,clean_text from jdk_api_valid"
    cursor.execute(sql)
    index=4586
    for res in cursor.fetchall()[4585:]:
        # 对每个api
        api_id=res[0]
        api_type=dict_api_type[res[1]]
        qualified_name=res[2]
        clean_text = res[3]
        clean_text = coref_resolved(clean_text,qualified_name,api_type)
        sql="UPDATE jdk_api_valid SET clean_text=%s WHERE api_id=%s"
        cursor.execute(sql,(clean_text,api_id))
        print("num:%d\tid:%d"%(index,api_id))
        index+=1
    db.commit()
    cursor.close()
    db.close()


#2.别名识别并保存
def alias_recognition():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    sql = "SELECT api_id,api_type,qualified_name,clean_text FROM jdk_api_valid"
    cursor.execute(sql)
    index=1
    for res in cursor.fetchall():
        api_id=res[0]
        api_type=dict_api_type[res[1]]
        qualified_name=res[2]
        clean_text=res[3]
        clean_text=nlp(clean_text)
        alias = get_alias(qualified_name)
        true_alias = set()
        true_alias.add(qualified_name)
        for sent in list(clean_text.sents):
            for word in sent:
                for a in alias:
                    if word.text==a:  # 前缀
                        true_alias.add(word.lemma_)
                        break
        true_alias.remove(qualified_name)
        for a in true_alias:
            sql="INSERT INTO api_alias (api_id, qualified_name, alias) values (%s,%s,%s)"
            cursor.execute(sql,(api_id,qualified_name,a))
        print("num:%d\tid:%d" % (index, api_id))
        index += 1
    db.commit()
    cursor.close()
    db.close()


#3.得到句子标签
def getTags():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    sql = "select api_id,api_type,qualified_name,clean_text from jdk_api_valid"
    cursor.execute(sql)
    fo = open("tag1", "w")
    for res in cursor.fetchall():
        # 对每个api
        api_id = res[0]
        api_type=dict_api_type[res[1]]
        qualified_name = res[2]
        document = res[3]
        document = nlp(document)
        try:
            fo.write(str(api_id) + "\n"+api_type + "\n"+qualified_name+"\n")
            for sent in list(document.sents):
                for word in sent:
                    fo.write(word.text+":"+word.pos_+"\n")
                fo.write("---STOP---\n")
            fo.write("\n")
            print(api_id)
        except UnicodeEncodeError as e:
            fo.write("---STOP---\n")
            fo.write("\n")
            pass
        continue

    fo.close()
    cursor.close()
    db.close()


#4.修改tag1的一些空行错误
def modified_error1():
    fr = open("tag1", "r")
    fw = open("tag2", "w")
    all = fr.readlines()
    i = 0
    k = 0
    while i < len(all):
        if (all[i] == "\n" and i + 1 < len(all) and not all[i + 1][:-1].isdigit()):
            i += 1
            continue
        elif ":" in all[i] and len(all[i][:-1].split(":")) != 2:
            i += 1
            continue
        else:
            fw.write(all[i])
            i += 1
            k += 1
            print(k)
    fr.close()
    fw.close()


#5.补全句子，删除无用句
def complete_sentence():
    fin = open("tag2", "r")
    fout = open("tag3", "w")
    i = 0
    all = fin.readlines()
    while i< len(all):
        line = all[i][:-1]
        if line.isdigit():
            id = line
            type = all[i + 1][:-1]
            qualified_name = all[i+2][:-1]
            string_write = id+"\n"+type+"\n"+qualified_name+"\n"
            i += 3
            while all[i] != "\n":
                words=[]
                tags=[]
                while all[i]!="---STOP---\n":
                    line=all[i][:-1].split(":")
                    words.append(line[0])
                    tags.append(line[1])
                    i+=1
                i+=1

                words,tags=useful_sentence(qualified_name,type,words,tags)
                if words:
                    if isinstance(words[0],list):#二维列表
                        for (sentence,sentence_tag) in zip(words,tags):
                            for (w,t) in zip(sentence,sentence_tag):
                                string_write+=w+":"+t+"\n"
                            string_write+="---STOP---\n"
                    else:
                        for (w, t) in zip(words, tags):
                            string_write += w + ":" + t + "\n"
                        string_write += "---STOP---\n"

            if string_write.count("\n") > 2:
                string_write += "\n"
                print(id)
                fout.writelines(string_write)
            i += 1
        else:
            i += 1
    fin.close()
    fout.close()


#6.替换别名
def replace_alias():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    fin = open("tag3", "r")
    fout = open("tag4","w")
    i = 0
    all = fin.readlines()
    while i < len(all):
        line = all[i][:-1]
        if line.isdigit():
            id = line
            type = all[i + 1][:-1]
            qualified_name = all[i + 2][:-1]
            string_write = id+"\n"+type+"\n"+qualified_name+"\n"
            sql="SELECT alias FROM api_alias WHERE api_id=%s"
            cursor.execute(sql,(id))
            alias = set()
            for a in cursor.fetchall():
                alias.add(a[0])
            i += 3
            while all[i] != "\n":
                words = []
                tags = []
                while all[i] != "---STOP---\n":
                    line = all[i][:-1].split(":")
                    words.append(line[0])
                    tags.append(line[1])
                    i += 1
                i += 1
                if words[0] in alias:
                    words[0]=qualified_name
                for (w, t) in zip(words, tags):
                    string_write += w + ":" + t + "\n"
                string_write += "---STOP---\n"
            if string_write.count("\n") > 2:
                string_write += "\n"
                print(id)
                fout.writelines(string_write)
            i += 1
        else:
            i += 1
    fin.close()
    fout.close()
    cursor.close()
    db.close()



#7.clean_text写回数据库
def write_to_database():
    db = pymysql.connect(host='localhost', user='root', passwd="123456", database='codehub', port=3306, charset='utf8')
    cursor = db.cursor()
    fin = open("tag4", "r")
    i = 0
    num = 1
    all = fin.readlines()
    while i < len(all):
        line = all[i][:-1]
        if line.isdigit():
            id = line
            clean_text=""
            i += 3
            while all[i] != "\n":
                words = []
                tags = []
                while all[i] != "---STOP---\n":
                    line = all[i][:-1].split(":")
                    words.append(line[0])
                    tags.append(line[1])
                    i += 1
                i += 1

                clean_text+=joint_sentence(words)

            if clean_text:
                sql="UPDATE jdk_api_valid SET clean_text=%s WHERE api_id=%s"
                cursor.execute(sql,(clean_text,id))
                print("num:%d\tid:%s"%(num,id))
                num+=1
            i += 1
        else:
            i += 1
    db.commit()
    fin.close()
    cursor.close()
    db.close()


#help.提及替换:指代消解；物主代词加's；the class替换
def coref_resolved(context,qualified_name,type):
    start_pos = 0
    doc = nlp(context)
    big_name=qualified_name.capitalize()
    if doc._.has_coref:
        to_replace = []
        for clust in doc._.coref_clusters:
            main_mention = clust.main
            for mention in clust.mentions:
                beg, end = mention.start_char - start_pos, mention.end_char - start_pos
                if end > 0:  # 是本句中的指代
                    if mention.text in ["its", "his", "her", "my", "your", "our", "their"]:
                        to_replace.append((beg, end, main_mention.text + "'s"))
                    else:
                        to_replace.append((beg, end, main_mention.text))
        to_replace = sorted(to_replace)  # 按照起始位置升序排序，为逐个替换做准备
        context = my_coref(context, to_replace)

    s = "the" + ' ' + type
    context = context.replace(s, qualified_name)
    s = "The" + ' ' + type
    context = context.replace(s, big_name)
    s = "this" + ' ' + type
    context = context.replace(s, qualified_name)
    s = "This" + ' ' + type
    context = context.replace(s, big_name)

    return context


#help.我的消解策略
def my_coref(orig_text,to_replace):
    left = 0
    processed_text = ""
    for beg,end,mention in to_replace:
        processed_text += orig_text[left:beg] + mention
        left = end
    processed_text += orig_text[left:]
    return processed_text


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


#help.删除可忽略词
def delete_ignore(line, line_tag):
    i=0
    while i <len(line):
        if line_tag[i] in IGNORE:
            del line[i]
            del line_tag[i]
        else:
            i+=1


#help.判断是否复杂句
def complex_sentence(line,line_tag):
    indexs=find_all(line,",")
    res=[]
    if indexs:
        for i in indexs:
            if i+1<len(line) and line[i+1]=="and":
                res.append(i)
    return res#可拆分处的索引


#help.找到某字符在字符串中的全部所索引
def find_all(line, s):
    r_list = []
    for r in range(len(line)):
        if line[r] == s:
            r_list.append(r)
    return r_list


#help.判断是否为有效句子
def useful_sentence(qualified_name,type,line,line_tag):
    if line==[] or line_tag==[]:
        return False,False
    if line[-1] =="?":
        return False,False
    delete_ignore(line, line_tag)
    if len(line)<=2:
        return False,False
    if line_tag[0]=="AUX" or line_tag[0] in BE:
        return False,False
    #剩下的句子分为：简单句；复杂句(包含 , and 可拆成两个句子)
    complex=complex_sentence(line,line_tag)
    if complex:#可拆分的复杂句
        complex = [-1] + complex
        lines = []
        line_tags = []
        for i in range(1, len(complex)):
            left = complex[i - 1] + 1
            right = complex[i]
            lines.append(line[left:right])
            line_tags.append(line_tag[left:right])
        line = []
        line_tag = []
        for (l, t) in zip(lines, line_tags):
            l,t=useful_sentence(qualified_name,type, l, t)
            if l:
                line.append(l)
                line_tag.append(t)
        if line:
            return line,line_tag
        else:
            return False,False

    else:
        #简单句处理
        if len(line)<=2:
            return False,False
        if line_tag[0] in NOUN or (line_tag[0]=='ADJ' and line_tag[1] in NOUN) or (line[0]=='"' and line[2]=='"' and line_tag[1] in NOUN):#noun开头
            if origin_type(line[0]) in APITYPE and contains(type,origin_type(line[0])):
                line[0] = line[0].lower()
                line.insert(0, qualified_name)
                line.insert(1, "contains")
                line_tag.insert(0, "NOUN")
                line_tag.insert(1, "VERB")
                return line,line_tag
            if line_tag[0] in NOUN:
                noun_index=0
            else:
                noun_index=1
            if noun_index+1<len(line_tag):
                if line_tag[noun_index+1]=="VERB":#主谓完整
                    return line,line_tag
                else:#不含谓语，API+is做主谓语
                    line[0]=line[0].lower()
                    line.insert(0, qualified_name)
                    line.insert(1, "is")
                    line_tag.insert(0, "NOUN")
                    line_tag.insert(1, "VERB")
                    return line,line_tag
            else:
                return False,False
        else:
            if line_tag[0]=="VERB":#缺主语 API名做主语
                line[0] = line[0].lower()
                line.insert(0,qualified_name)
                line_tag.insert(0,"NOUN")
                return line,line_tag
            else:#病句无效句，查看可得
                return False,False



#help.判断两种API类型是否为包含关系（type1包含type2）
def contains(type1,type2):
    types=[{"package","packages"},{"interface","interfaces"},{"class","classes"},{"method","methods"}]
    index1=-1
    index2=-1
    for i in range(len(types)):
        if type1 in types[i]:
            index1=i
            break
    for i in range(len(types)):
        if type2 in types[i]:
            index2=i
            break
    if index1!=-1 and index2!=-1:
        return index1<index2
    else:
        return False


#help.将API类型的单词（复数形式）变为原型
def origin_type(type):
    type=type.lower()
    dict_api_type={"packages":"package","interfaces":"interface","classes":"class","methods":"method"}
    if type in dict_api_type.keys():
        return dict_api_type[type]
    if type in dict_api_type.values():
        return type
    return type


#help.将一个字符串列表拼成一个句子
def joint_sentence(line):
    s=""
    for word in line:
        if word in string.punctuation:
            s=s[:-1]+word+" "
        else:
            s+=word+" "
    if line[-1] not in string.punctuation:
        s = s[:-1] + ". "
    return s


if __name__ == '__main__':
    # getTags()
    # modified_error1()
    #complete_sentence()
    replace_alias()
    write_to_database()

