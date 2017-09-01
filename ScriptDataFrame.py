import pandas as pd

def CreateTable():
    Table=pd.DataFrame(columns=('LinacID','Energy','Output','FlatX','FlatY','SymX','SymY','MPV','Date','Time','Initials'))
    return Table

def InsertRow(Table,Index,ContentList):
    Table.loc[Index]=ContentList

def SaveTable(Table,PathWithFN):
    Table.to_pickle(PathWithFN)


def ReadTable(PathWithFN):
    Table=pd.read_pickle(PathWithFN)
    return Table

def ConvertToXLS(Table,PathWithFN):
        Table.to_excel(PathWithFN,sheet_name='DailyQA')



# # #Example usage
# tt=CreateTable()
# InsertRow(tt,0,['LA4','6X',1.5,1.2,0.8,0.6,-1.9])
# InsertRow(tt,1,['LA2','18X',1.5,1.2,0.8,0.6,-1.9])
# SaveTable(tt,'D:\\DailyCheck\\Table')
# tr=ReadTable('D:\DailyCheck\Table')
# print(tr.count()[1])
# #print(tt)

# NewTable=CreateTable()
# SaveTable(NewTable,'D:\\DailyCheck\\Table')

