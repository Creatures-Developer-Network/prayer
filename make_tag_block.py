from prayer import tag_block

data = list()
data.append(("string variable no 1","moep moep moep"))
data.append(("Cat :D", "The domestic cat or the feral cat is a small, typically furry, carnivorous mammal. They are often called house cats when kept as indoor pets or simply cats when there is no need to distinguish them from other felid..."))
data.append(("Some Magic Number", 42))
data.append(("String with weird Latin characters", "éèáÁáàäöüß"))
data.append(("blue", "Yo listen up here's a story\nAbout a little guy that lives in a blue world\nAnd all day and all night and everything he sees Is just blue\nLike him inside and outside\nBlue his house with a blue little window\nAnd a blue Corvette\nAnd everything is blue for him\nAnd himself and everybody around\n'Cause he ain't got nobody to listen."))
data.append(("LEET", 1337))

tag_block.generate_tag_block('MOEP','MyPersonalDummyTagBlock',False,data)
with open('resources/%s.blk' % 'MOEP', 'wb') as f:

    f.write(bytes('PRAY',encoding='latin-1') + tag_block.generate_tag_block('MOEP','MyPersonalDummyTagBloack',False,data))