import requests,re,json,pymongo,os
from math import ceil
from urllib.parse import urlencode
from urllib.request import urlretrieve
from config import *
client=pymongo.MongoClient(mongo_url)
db=client[mongo_db]
#获取索引页的json数据
def get_index_page(index_url,pagenum):
    form_data={
         b'cb': b'Callback',
         b'id': b'TOPC1451464884159276',
         b'n': b'20',
         b'of': b'fdate',
         b'p': pagenum,
         b'serviceId': b'tvcctv',
         b'type': b'0'
    }
    index_page=requests.get(index_url+urlencode(form_data)).text
    return index_page
#解析json数据,获得预览信息，返回一个列表，包括：详情页url，视频简介，视频长度
def parse_index_page(index_page):
    pattern=re.compile('Callback\((.*?)\);',re.S)
    response=re.findall(pattern,index_page)[0]
    response_json=json.loads(response)
    pre_info=response_json['response']
    return pre_info
#根据详情页html获取每一个详情页的pid
def get_pid(detai_url):
    html = requests.get(detai_url).text
    pid = re.findall('var guid = "(.*?)"', html)[0]
    return pid
#根据pid拼接出央视影音app中每一个视频的接口地址，获取分段视频下载地址
def get_Video_Info(pid,pre_info):
    part_url = 'http://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid='
    response=requests.get(part_url+pid).text
    response_json=json.loads(response)
    title=response_json['tag']
    time=response_json['f_pgmtime']
    video=response_json['video']['chapters4']
    video_url=[]
    for i in video:
        video_url.append(i['url'])
    return{
            'title': title,
            'time': time,
            'videoBrief':pre_info['videoBrief'],
            'videoLength':pre_info['videoLength'],
            'video_url': video_url
        }
#下载视频
def download_videos(video_info):
    video_url=video_info['video_url']
    #txt文件的文件名
    filename = '{}.txt'.format(video_info['title'])
    #合并之前的视频名，合并之后删除
    del_list=[]
    for index,item in enumerate(video_url):
        print('正在打印第{}页'.format(index+1),item)
        urlretrieve(item,video_info['title']+'-'+str(index+1)+'.mp4')
        #创建一个txt文件，在每行写入file '待合并的视频名称'
        with open(filename, 'a+')as f:
            f.write('file '+"'"+video_info['title']+'-'+str(index+1)+'.mp4\n')
            #把分段视频的名称装进del_list中
            del_list.append(video_info['title']+'-'+str(index+1)+'.mp4')
    #合并视频
    contact_videos(filename)
    #删除分段视频文件
    for i in del_list:
        os.remove(i)
    #删除txt文件
    os.remove(filename)
#调用os.system（）让FFmpeg合并视频
def contact_videos(filename):
    order="ffmpeg -y -f concat -safe 0 -i %s -c copy %s.mp4" % (filename, filename[:-5])
    os.system(order)
#保存到数据库
def save_to_mongodb(video_info):
    if db[mongo_table].insert_one(video_info):
        return True
    else:
        return False
#启动，page_num为页数，order_num为视频在当前页面的位置
def main():
    #视频列表的接口
    index_url='http://api.cntv.cn/lanmu/videolistByColumnId?'
    index_page=get_index_page(index_url,1)
    #获得视频数量
    page_num_ceil=parse_index_page(index_page)['numFound']
    #每页15个视频，向上取整获得页数
    page_nums=ceil(page_num_ceil/15)
    print(page_nums)
    for page_num in range(1,int(page_nums)+1):
        print('正在下载第{}页视频'.format(page_num))
        index_page = get_index_page(index_url, page_num)
        for i in parse_index_page(index_page)['docs']:
            pid = get_pid(i['videoUrl'])
            video_info = get_Video_Info(pid, i)
            if video_info:
                save_to_mongodb(video_info)
            download_videos(video_info)
if __name__ == '__main__':
    main()


