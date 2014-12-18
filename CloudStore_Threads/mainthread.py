import cgi
import webapp2
import jinja2
import random
import os
import sys
import threading

sys.path.append('lib')
import cloudstorage as gcs
# Importing Google App Engine API
from google.appengine.api import memcache
from datetime import datetime

# JINJA Environment variables
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

# GCS Retry Parameters
my_default_retry_params = gcs.RetryParams(initial_delay=0.2,
                                          max_delay=5.0,
                                          backoff_factor=2,
                                          max_retry_period=15)
gcs.set_default_retry_params(my_default_retry_params)

memcache_filenames = []
gcs_filenames = []

# Google Cloud Storage Bucket Name
bucket_name = 'Bucket_Name'

# Thread Class
class myThread(threading.Thread):
    # Thread Initialization
    def __init__(self, function, filename, filecontent):
        threading.Thread.__init__(self)
        self.function = function
        self.filename = filename
        self.filecontent = filecontent
    # Thread Run
    def run(self):
        # Insert Block
        if str(self.function) == "insert":
                try:
                    filelength = len(self.filecontent)

                    #MEMCACHE Insert Block
                    if filelength<=102400:
                        memcache.add(self.filename,self.filecontent,3600)
                        memcache_filenames.append(str(self.filename))

                    #GCS Insert Block
                    write_retry_params = gcs.RetryParams(backoff_factor=1.1)
                    gcs_file = gcs.open(bucket_name+"/"+self.filename,'w',content_type='text/plain',options=None,retry_params=write_retry_params)
                    gcs_file.write(self.filecontent)
                    gcs_file.close()
                    gcs_filenames.append(str(self.filename))

                except Exception:
                    print 'Error While Uploading File:' + str(self.filename)

        # Find Block Without Memcache
        elif str(self.function) == "findall_wom":
                try:
                    #Get GCS BucketList
                    stats = gcs.listbucket(bucket_name)
                    count = 0
                    for stat in stats:
                        self.response.write("<br>"+self.filename)
                        count+=1

                    if count == 0:
                        self.response.write(" Status Code: 0")
                    count = None
                    stats = None
                except Exception:
                    print 'Status Code: 0'

        # Find Block With Memcache
        elif str(self.function) == "findall_wm":
                try:
                    #Get GCS Bucket List & Memcache List
                    stats = gcs.listbucket(bucket_name)
                    count = 0
                    for stat in stats:
                        count=count+1
                        matched = re.search(r'/cloudstore-storage/(.*)', stat.filename)
                        filename = matched.group(1)
                        filecontent = memcache.get(filename)
                        if filecontent != None:
                            self.response.write("Memcache Files: "+ filename +"<br>")
                        else:
                            self.response.write("GCS Files: "+ stat.filename +"<br>")

                    if count == 0:
                        filecontent = memcache.get('Master')
                        if len(memcache.get('Master')) > 0:
                            for files in filecontent:
                                filedata = memcache.get(files)
                                if filedata != None:
                                    self.response.write("Memcache Files: "+ files +"<br>")
                                else:
                                        count = -1
                        else:
                            self.response.write("Status Code: 0")

                    if count == -1:
                        self.response.write("Status Code: 0")
                except Exception:
                    print 'Status Code: 0'

        # GCS Remove All Bucket Files
        elif str(self.function) == "gcs_remove":
                try:
                    # GCS Delete
                    gcs.delete(self.filename)
                except Exception as e:
                    print 'Error while deleting File: ' + str(self.filename)

        # GCS and Memcahe Remove all Files
        elif str(self.function) == "all_remove":
                try:
                    # Memcache Delete
                    if memcache.delete(self.filename) == 2:
                        memcache_filenames.remove(self.filename)
                    # GCS Delete
                    gcs.delete(self.filename)
                    memcache_filenames.remove(self.filename)
                except Exception as e:
                    print 'Mem and GCS Delete'
                    
# Main Page Webapp2 Request Handler
class MainPage(webapp2.RequestHandler):
    
    # Get Methos
    def get(self):
        # Initializing response type and creating Jinja template
        self.response.headers['Content-Type'] = 'text/html'
        template = JINJA_ENVIRONMENT.get_template('threadindex.html')
        # Rendering the webpage
        self.response.write(template.render())
        memcache.add('Master',memcache_filenames,18000)
    
    # Post Method for handling the Client Request
    def post(self):
        # rparams contains the POST method Request Objects
        rparams = self.request.POST.items();
        function = None
        data = None
        fn, fd = rparams[0]
        req_count =len(rparams)
        req_bal = req_count%4        
        req_val = req_count-req_bal
        count = 0
        ch=1
        write_retry_params = gcs.RetryParams(backoff_factor=1.1)

        # Insert Form Submission
        if str(fn) == "insert":
            ct = datetime.now()
            st = ct.microsecond
            if req_count >=4:            
                for i in range(0,req_val,4):
                    try:
                        count=count+1
                        threads = []
                        function, data = rparams[i]
                        # Thread initialization
                        thread1 = myThread(function,data.filename,data.value)
                        threads.append(thread1)
                        i+=1
                        count=count+1
                        function, data = rparams[i]
                        # Thread initialization
                        thread2 = myThread(function,data.filename,data.value)
                        threads.append(thread2)
                        i+=1
                        count=count+1
                        function, data = rparams[i]
                        # Thread initialization
                        thread3 = myThread(function,data.filename,data.value)
                        threads.append(thread3)
                        i+=1
                        count=count+1
                        function, data = rparams[i]
                        # Thread initialization
                        thread4 = myThread(function,data.filename,data.value)
                        threads.append(thread4)

                        # Starting Threads
                        thread1.start()
                        thread2.start()
                        thread3.start()
                        thread4.start()

                        # Threads Join
                        for t in threads:
                            t.join()

                    except Exception as e:
                        ch=2
                req_count = req_count - count

            if req_count<4:

                for i in range(count,len(rparams),1):
                    try:
                        function, data = rparams[i]
                        # Thread initialization
                        thread1 = myThread(function,data.filename,data.value)
                        # Threads Start
                        thread1.start()
                        # thread Join
                        thread1.join()
                    except Exception as e:
                        ch=2
            count=0
            ct = datetime.now()
            et = ct.microsecond

        # Find Operation Without Memcache
        if str(fn) == "findall_wom":
            ct = datetime.now()
            st = ct.microsecond
            ch=0
            filecount=0
            count=0
            filename_list = []
            # get GCS Bucket List
            stats = gcs.listbucket(bucket_name)
            for stat in stats:
                filecount=filecount+1
                filename_list.append(stat.filename)
                self.response.write(stat.filename)
            print filecount
            print filename_list
            if filecount>=4:
                for i in range(0,(filecount-(filecount%4)),4):
                    try:
                        print i
                        count=count+1
                        thread1 = myThread(fn,filename_list[i],'')
                        i+=1
                        count=count+1
                        thread2 = myThread(fn,filename_list[i],'')
                        i+=1
                        count=count+1
                        thread3 = myThread(fn,filename_list[i],'')
                        i+=1
                        count=count+1
                        thread4 = myThread(fn,filename_list[i],'')

                        thread1.start()
                        thread2.start()
                        thread3.start()
                        thread4.start()
                        thread1.join()
                        thread2.join()
                        thread3.join()
                        thread4.join()
                    except Exception as e:
                        self.response.write(e)
                filecount=filecount-count
            if filecount<4:
                for i in range(count,len(filename_list),1):
                    try:
                        thread1 = myThread(fn,filename_list[i],'')
                        thread1.start()
                        thread1.join()
                    except Exception as e:
                        self.response.write(e)
            ct = datetime.now()
            et = ct.microsecond

        # Find Operation With Memcache
        if str(fn) == "findall_wm":
            ct = datetime.now()
            st = ct.microsecond
            ch=0
            filecount=0
            count=0
            filename_list = []
            # get GCS Bucket List
            stats = gcs.listbucket(bucket_name)
            for stat in stats:
                filecount=filecount+1
                filename_list.append(stat.filename)
            # get Memcache List
            filecontent = memcache.get('Master')
            if len(memcache.get('Master')) > 0:
                for files in filecontent:
                    filecount=filecount+1
                    filename_list.append(files)
            print filecount
            print filename_list
            if filecount>=4:
                for i in range(0,(filecount-(filecount%4)),4):
                    try:
                        count=count+1
                        thread1 = myThread(fn,filename_list[i],'')
                        i+=1
                        count=count+1
                        thread2 = myThread(fn,filename_list[i],'')
                        i+=1
                        count=count+1
                        thread3 = myThread(fn,filename_list[i],'')
                        i+=1
                        count=count+1
                        thread4 = myThread(fn,filename_list[i],'')

                        thread1.start()
                        thread2.start()
                        thread3.start()
                        thread4.start()
                        thread1.join()
                        thread2.join()
                        thread3.join()
                        thread4.join()
                    except Exception as e:
                        self.response.write(e)
                filecount=filecount-count
            if filecount<4:
                for i in range(count,len(filename_list),1):
                    try:
                        thread1 = myThread(fn,filename_list[i],'')
                        thread1.start()
                        thread1.join()
                    except Exception as e:
                        self.response.write(e)
            ct = datetime.now()
            et = ct.microsecond

        # Remove all GCS Files 
        if str(fn) == "gcs_remove":
            filecount=0
            count=0
            filename_list = []
            ch=2
            # get GCS File List
            stats = gcs.listbucket(bucket_name)
            for stat in stats:
                filecount=filecount+1
                filename_list.append(stat.filename)
            ct = datetime.now()
            st = ct.microsecond
            if filecount>=4:
                for i in range(0,(filecount-(filecount%4)),4):
                    try:
                        ch=1
                        count=count+1
                        thread1 = myThread(fn,filename_list[i],'')
                        i+=1
                        count=count+1
                        thread2 = myThread(fn,filename_list[i],'')
                        i+=1
                        count=count+1
                        thread3 = myThread(fn,filename_list[i],'')
                        i+=1
                        count=count+1
                        thread4 = myThread(fn,filename_list[i],'')

                        thread1.start()
                        thread2.start()
                        thread3.start()
                        thread4.start()
                        thread1.join()
                        thread2.join()
                        thread3.join()
                        thread4.join()
                    except Exception as e:
                        ch=2
                filecount=filecount-count
            if filecount<4:
                for i in range(count,len(filename_list),1):
                    try:
                        ch=1
                        thread1 = myThread(fn,filename_list[i],'')
                        thread1.start()
                        thread1.join()
                    except Exception as e:
                        ch=2
            ct = datetime.now()
            et = ct.microsecond

        # Remove all Files from GCS and Memcache
        if str(fn) == "all_remove":
            ch=2
            filecount=0
            count=0
            filename_list = []
            # get GCS Bucket List
            stats = gcs.listbucket(bucket_name)
            for stat in stats:
                filecount=filecount+1
                filename_list.append(stat.filename)
            # get Memcache List
            filecontent = memcache.get('Master')
            if len(memcache.get('Master')) > 0:
                for files in filecontent:
                    filecount=filecount+1
                    filename_list.append(files)
            ct = datetime.now()
            st = ct.microsecond
            if filecount>=4:
                for i in range(0,(filecount-(filecount%4)),4):
                    try:
                        ch=1
                        count=count+1
                        thread1 = myThread(fn,filename_list[i],'')
                        i+=1
                        count=count+1
                        thread2 = myThread(fn,filename_list[i],'')
                        i+=1
                        count=count+1
                        thread3 = myThread(fn,filename_list[i],'')
                        i+=1
                        count=count+1
                        thread4 = myThread(fn,filename_list[i],'')

                        thread1.start()
                        thread2.start()
                        thread3.start()
                        thread4.start()
                        thread1.join()
                        thread2.join()
                        thread3.join()
                        thread4.join()
                    except Exception as e:
                        ch=2
                filecount=filecount-count
            if filecount<4:
                for i in range(count,len(filename_list),1):
                    try:
                        ch=1
                        thread1 = myThread(fn,filename_list[i],'')
                        thread1.start()
                        thread1.join()
                    except Exception as e:
                        ch=2
            ct = datetime.now()
            et = ct.microsecond

        # Generating Master File
        memcache.replace('Master',memcache_filenames,18000)

        if ch == 1:
            self.response.write("Status Code : 1<br>")
        if ch == 2:
            self.response.write("Status Code: 0<br>")
        tt = et - st
        self.response.write('Time Taken = ' + str(tt) + ' microsecond')

# FindAllFiles Web Request Handler for Multiple File Downloads
class FindALLFiles(webapp2.RequestHandler):
    def get(self):
        try:
            ch=0
            cacheFlag=self.request.get("cacheFlag")
            print("cache flag recieved",cacheFlag);
            # cacheFlag = False; Fetch list from GCS
            if str(cacheFlag)=="false":
                stats = gcs.listbucket(bucket_name)
                print("accessing gcs bucket");
                count = 0
                for stat in stats:
                    self.response.write(stat.filename+";")
                    count+=1 
                print("total no of files in GCS: "+count)
                if count == 0:
                    self.response.write("No data found :404")
            # cacheFlag = False; Fetch list from Memcache
            else:
                print("in else part");
                filecontent = memcache.get('Master')
                print(filecontent)
                if len(memcache.get('Master')) > 0:
                    print("fetching memcache list")
                    for files in filecontent:
                        filedata = memcache.get(files)
                        if filedata != None:
                            self.response.write(files+";")
                        else:
                            count = -1
            count = None
            stats = None
        except Exception as e:
            print type(e)
            print "server exception"

# # FindAllFiles Web Request Handler for Multiple File Downloads
class downloadFiles(webapp2.RequestHandler):
    def get(self):
        try:
            ch=0
            # getting Download File from Client
            dlFileName=self.request.get("action");
            cacheFlag=self.request.get("cacheFlag");
            # cacheFlag = False; Fetch list from GCS
            if str(cacheFlag)=="false":
                filecontent = memcache.get(str(dlFileName))
                if filecontent != None:
                    self.response.write("Memcache File Content:")
                    self.response.write("<br>"+filecontent+"")

                stat = gcs.stat(bucket_name+"/"+str(dlFileName))
                gcs_file = gcs.open(bucket_name+"/"+str(dlFileName),'r')
                filecontent=gcs_file.read()
                fileName=str(dlFileName)
                self.response.write(filecontent)
                gcs_file.close()
                stat = None
            # cacheFlag = False; Fetch list from Memcache
            else:
                filecontent = memcache.get(str(dlFileName))
                print("printing memcache filecontent to response");
                self.response.write(filecontent);

        except Exception:
            print "server exception"
            self.response.write("")
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/findAll',FindALLFiles),
    ('/download',downloadFiles),
], debug=True)