import cgi
import webapp2
import jinja2
import random
import os
import sys
import urlparse
import gzip
import StringIO
from datetime import datetime
sys.path.append('lib')
import cloudstorage as gcs

from google.appengine.api import memcache
#JINJA Environment variables initialization
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# Google AppEngine retry parameters
my_default_retry_params = gcs.RetryParams(initial_delay=0.2,
                                          max_delay=5.0,
                                          backoff_factor=2,
                                          max_retry_period=15)
gcs.set_default_retry_params(my_default_retry_params)

memcache_filenames = []
# GCS Bucket Name
bucket_name = '/cloudstore-storage'

# Main Page Webpage Request Handler
class MainPage(webapp2.RequestHandler):

    def get(self):
        # Rendering the Webpage of the Application
        self.response.headers['Content-Type'] = 'text/html'
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render())
        # Master file is used to keep track Files present in Memcache
        memcache.add('Master',memcache_filenames,18000)

    # Form Request Handler
    def post(self):
        # rparams obtains http request object
        rparams = self.request.POST.items();
        print(len(rparams))
        write_retry_params = gcs.RetryParams(backoff_factor=1.1)
        ch = 1
        totaltime=0
        #Iterate over the rparameters to obtain the form data
        for rparam in rparams:
            # Insert Function Block
            if str(rparam[0]) == "insert":

                try:
                    dt = datetime.now()
                    st=dt.microsecond
                    filename = rparam[1].filename
                    filecontent = rparam[1].value
                    filelength = len(filecontent)

                    # MEMCACHE Insert BLOCK
                    if filelength<=102400:
                        memcache.add(filename,filecontent,3600)
                        memcache_filenames.append(str(filename))
                    # GCS Insert BLOCK
                    gcs_file = gcs.open(bucket_name+"/"+filename,'w',content_type='text/plain',options=None,retry_params=write_retry_params)
                    gcs_file.write(filecontent)
                    gcs_file.close()
                    ch = 1
                    dt = datetime.now()
                    et=dt.microsecond
                    print(" Time Taken: "+str(et-st)+" microseconds")
                    totaltime+=(et-st)
                    memcache.replace('Master',memcache_filenames,18000)
                    filename = None
                    filecontent = None
                    filelength = None
                    write_retry_params = None

                except Exception as e:
                    ch = 2
            #Check File Block
            elif str(rparam[0]) == "check":

                try:
                    ch=0
                    # Checks if the file is present in the Memcache or GCS
                    filecontent = memcache.get(str(rparam[1]))
                    if filecontent != None:
                        self.response.write("Status Code: 1<br>")
                    else:
                        stat = gcs.stat(bucket_name+"/"+str(rparam[1]))
                        self.response.write("Status Code: 1<br>")
                        stat = None
                    filecontent = None

                except Exception:
                    self.response.write("Status Code: 0")
            # Find File Block
            elif str(rparam[0]) == "find":

                try:
                    dt = datetime.now()
                    st=dt.microsecond
                    ch=0
                    # Download the File from Memcache if present else from GCS
                    filecontent = memcache.get(str(rparam[1]))
                    if filecontent != None:
                        self.response.headers.add_header('Content-Type','application/octet-stream')
                        self.response.headers.add_header('Content-Disposition',"attachment;filename="+fileName)
                        self.response.write(filecontent)
                    else:
                        stat = gcs.stat(bucket_name+"/"+str(rparam[1]))
                        gcs_file = gcs.open(bucket_name+"/"+str(rparam[1]),'r')
                        fileName=str(rparam[1])
                        filecontent=gcs_file.read()
                        self.response.headers.add_header('Content-Type','application/octet-stream')
                        self.response.headers.add_header('Content-Disposition',"attachment;filename="+fileName)
                        self.response.write(filecontent)
                        gcs_file.close()
                        stat = None
                    dt = datetime.now()
                    et=dt.microsecond
                    print(" Time Taken: "+str(et-st)+" microseconds")
                    totaltime+=(et-st)
                       
                    filecontent = None

                except Exception:
                    self.response.write("Status Code: 0")
            # Remove File Block
            elif str(rparam[0]) == "remove":

                try:
                    ch=0
                    dt = datetime.now()
                    st=dt.microsecond
                    # Removes the present in Both GCS and Memcache based on File Hit
                    filecontent = memcache.get(str(rparam[1]))
                    count = 0
                    if filecontent != None:
                        if memcache.delete(str(rparam[1])) == 2:
                            count = count+1
                            memcache_filenames.remove(str(rparam[1]))

                    gcs.delete(bucket_name+"/"+str(rparam[1]))
                    count = count+1

                    if count>0:
                        self.response.write("Status Code: 1<br>")
                    else:
                        self.response.write("Status Code: 0<br>")
                    dt = datetime.now()
                    et=dt.microsecond
                    print(" Time Taken: "+str(et-st)+" microseconds")
                    totaltime+=(et-st)
                    memcache.replace('Master',memcache_filenames,18000)
                except Exception:
                    self.response.write("Status Code: 0")
            # List all the files present in the GCS
            elif str(rparam[0]) == "list":
                dt = datetime.now()
                st=dt.microsecond
                print(st)
                try:
                    ch=0
                    stats = gcs.listbucket(bucket_name)
                    count = 0
                    for stat in stats:
                            self.response.write("<br>"+stat.filename)
                            count+=1 

                    if count == 0:
                        self.response.write(" Status Code: 0")
                    count = None
                    stats = None
                    dt = datetime.now()
                    et=dt.microsecond
                    print(" Time Taken: "+str(et-st)+" microseconds")
                    totaltime+=(et-st)                    

                except Exception:
                    self.response.write(" Status Code: 0")
            #Find all files without memcache
            elif str(rparam[0]) == "findall_wom":
                try:
                    ch=0
                    dt = datetime.now()
                    st=dt.microsecond
                    stats = gcs.listbucket(bucket_name)
                    count = 0
                    for stat in stats:
                        self.response.write("<br>"+stat.filename)
                        count+=1

                    if count == 0:
                        self.response.write(" Status Code: 0")
                    count = None
                    stats = None
                except Exception:
                    self.response.write(" Status Code: 0")
            #Find all files with memcache
            elif str(rparam[0]) == "findall_wm":
                try:
                    ch=0
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

                    count = None
                    stats = None
                except Exception:
                    self.response.write("Status Code: 0")
            #Find file in GCS
            elif str(rparam[0]) == "gcs_check":
                try:
                    ch=0
                    stat = gcs.stat(bucket_name+"/"+str(rparam[1]))
                    self.response.write("Status Code: 1<br>")
                    stat = None

                except Exception:
                    self.response.write("Status Code: 0")
            #Find given file memcache
            elif str(rparam[0]) == "mc_check":
                try:
                    ch=0
                    filecontent = memcache.get(str(rparam[1]))
                    if filecontent != None:
                        self.response.write("Status Code: 1<br>")
                    else:
                        self.response.write("Status Code: 0<br>")

                    filecontent = None

                except Exception:
                    self.response.write("Status Code: 0")
            #Remove given file from memcache
            elif str(rparam[0]) == "mc_remove":
                try:
                    dt = datetime.now()
                    st=dt.microsecond
                    ch=0                    
                    filecontent = memcache.get('Master')
                    if len(memcache.get('Master')) > 0:
                        for files in filecontent:
                                if memcache.delete(files) == 2:
                                    ch=1
                                    memcache_filenames.remove(files)
                                    memcache.replace('Master',memcache_filenames,18000)
                                else:
                                    ch=2
                    else:
                        self.response.write("Status Code: 0")

                    stats = None
                    count = None
                    dt = datetime.now()
                    et=dt.microsecond
                    print(" Time Taken: "+str(et-st)+" microseconds")
                    totaltime+=(et-st)
                except Exception as e:
                    self.response.write(e)
            #Remove given file from GCS
            elif str(rparam[0]) == "gcs_remove":
                try:
                    dt = datetime.now()
                    st=dt.microsecond
                    ch=0
                    stats = gcs.listbucket(bucket_name)
                    count = 0
                    for stat in stats:
                        gcs.delete(stat.filename)
                        count=count+1
                    if count>0:
                        self.response.write("Status Code: 1<br>")
                    else:
                        self.response.write("Status Code: 0<br>")

                    stats = None
                    count = None
                    dt = datetime.now()
                    et=dt.microsecond
                    print("Time Taken"+str(et-st)+" microseconds");
                    totaltime+=(et-st)
                except Exception:
                    self.response.write("Status Code: 0")
            #Remove all the files from Memcache And GCS
            elif str(rparam[0]) == "all_remove":

                try:
                    dt = datetime.now()
                    st=dt.microsecond
                    
                    ch=0
                    stats = gcs.listbucket(bucket_name)
                    count = 0
                    for stat in stats:
                        gcs.delete(stat.filename)
                        count=count+1
                    print("deleted from GCS")
                    filecontent = memcache.get('Master')
                    if len(memcache.get('Master')) > 0:
                        for files in filecontent:
                            if memcache.delete(files) == 2:
                                count=count+1
                            memcache_filenames.remove(files)
                    print("deleted from cache")
                    if count>0:
                        self.response.write("Status Code: 1<br>")
                    else:
                        self.response.write("Status Code: 0<br>")
                    dt = datetime.now()
                    et=dt.microsecond
                    print("Time Taken"+str(et-st)+"microseconds");
                    totaltime+=(et-st)
                    stats = None
                    count = None
                    memcache.replace('Master',memcache_filenames,18000)
                except Exception as e:
                    print type(e)
                    print "server exception"
                    self.response.write("Status Code: 0")                    
            #Calculate Total size for all the files present in memcache
            elif str(rparam[0]) == "cache_size":
                try:
                    ch=0
                    size = 0.0
                    filecontent = memcache.get('Master')
                    if len(memcache.get('Master')) > 0:
                        for files in filecontent:
                            filedata = memcache.get(files)
                            if filedata != None:
                                size = size + len(filedata)

                    self.response.write(str((size/(1024*1024))) + " MB<br>")
                    stats = None
                    size = None
                    
                except Exception:
                    self.response.write("Status Code: 0")
            #Count total no of file in Memcache
            elif str(rparam[0]) == "cache_file_count":
                try:
                    ch=0
                    count = len(memcache.get('Master'))
                    self.response.write(str(count) + " Files<br>")
                    stats = None
                    count = None
                    
                except Exception:
                    self.response.write("Status Code: 0")
            #Calculate Total size for all the files present in GCS
            elif str(rparam[0]) == "gcs_size":
                try:
                    ch=0
                    stats = gcs.listbucket(bucket_name)
                    size = 0.0
                    for stat in stats:
                        gcs_file = gcs.open(stat.filename,'r')
                        size = size + len(gcs_file.read())
                        gcs_file.close()
                            
                    self.response.write(str((size/(1024*1024))) + " MB<br>")
                    stats = None
                    size = None
                    
                except Exception:
                    self.response.write("Status Code: 0")
            #Count total no of file in GCS
            elif str(rparam[0]) == "gcs_file_count":
                try:
                    ch=0
                    stats = gcs.listbucket(bucket_name)
                    count = 0
                    for stat in stats:
                        count=count+1;
                            
                    self.response.write(str(count) + " Files<br>")
                    stats = None
                    count = None
                    
                except Exception:
                    self.response.write("Status Code: 0")
            #Search for file Name
            elif str(rparam[0]) == "file_key":
                ch=0
                key = str(rparam[1])
            #Search for regex inside the file
            elif str(rparam[0]) == "value_re":
                try:
                    ch=0
                    value_re = str(rparam[1])
                    filecontent = memcache.get(key)
                    if filecontent != None:
                        if filecontent.find(value_re) > 0:
                            self.response.write("Status Code: 1<br>")
                        else:
                            self.response.write("Status Code: 0<br>")
                        
                    else:
                        stat = gcs.stat(bucket_name+"/"+key)
                        gcs_file = gcs.open(bucket_name+"/"+key,'r')
                        if gcs_file.read().find(value_re) > 0:
                            self.response.write("Status Code: 1<br>")
                        else:
                            self.response.write("Status Code: 0<br>")
                        gcs_file.close()
                        stat = None
                    key = None
                    value_re = None
                    filecontent = None
                    
                except Exception:
                    self.response.write("Status Code: 0")
            #Search regex for file name
            elif str(rparam[0]) == "file_re":
                try:
                    ch=0
                    exp = str(rparam[1])
                    count = 0
                    stats = gcs.listbucket(bucket_name)
                    for stat in stats:
                        if stat.filename.find(exp) > 0:
                            self.response.write(stat.filename + "<br>")
                            count=count+1

                    if count == 0:
                        self.response.write("Status Code: 0")

                    stats = None
                    exp = None
                    
                except Exception:
                    self.response.write("Blah Status Code: 0")

            else:
                print 'Error'
        
        #print "Master"
        # memcache.replace('Master',memcache_filenames,18000)
        print ch
        if ch == 1:
            self.response.write("Status Code : 1<br>")

        if ch == 2:
            self.response.write("Status Code: 0<br>")

        self.response.write("TimeTaken: "+str(totaltime) +" microseconds") 
        print("TimeTaken: "+str(totaltime) +" microseconds")
        rparams = None

#File the list of files based on CacheFlag and handle asynchronous request
class FindALLFiles(webapp2.RequestHandler):
    def get(self):
        try:
            ch=0
            cacheFlag=self.request.get("cacheFlag")
            print("cache flag recieved",cacheFlag);
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
# Handle multiple Asynchronous request and download content to disk
class downloadFiles(webapp2.RequestHandler):
    def get(self):
        try:
            ch=0
            dlFileName=self.request.get("action");
            cacheFlag=self.request.get("cacheFlag");
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
            else:
                filecontent = memcache.get(str(dlFileName))
                print("printing memcache filecontent to response");
                self.response.write(filecontent);

        except Exception:
            print "server exception"
            self.response.write("")
# Handle multiple request for batch file upload and merge data for files with size greater then 20MB
class TestPage(webapp2.RequestHandler):
    def post(self):
        print("processing part");
        out = StringIO.StringIO()
        rparams = self.request.POST.items();
        qr=self.request.query_string
        chunksize=len(str(rparams[0]));
        part =dict(urlparse.parse_qsl(qr))
        print(part);    
        if part["part"]<part["last"]:
            key=part["part"];
            print("key value",key)
            memcache_filenames[key]=str(rparams[0]);
            print(len(str(rparams[0])))
            print("streaming data for part :",key);
        else:            
            key=part["part"];
            print("key value::",key)
            memcache_filenames[key]=str(rparams[0]);
            print("streaming data for part :",key);
            n=int(part["last"])
            print(n)
            content = "";
        for x in range(0, n+1):
            content+=memcache_filenames[str(x)]
        print("before compression",len(content));

        with gzip.GzipFile(fileobj=out, mode="w") as f:
            f.write(content);
        print("after compression::");
        print(out.len);
        try:
            filename = memcache_filenames["fileName"]
            filecontent = out
            filelength = out.len
            #MEMCACHE BLOCK
            if filelength<=102400:
                memcache.add(filename,filecontent,3600)
                memcache_filenames.append(filename)
            print("Writing to GCS; size befoe compression:",filelength);    
            write_retry_params = gcs.RetryParams(backoff_factor=1.1)
            gcs_file = gcs.open(bucket_name+"/"+filename,'w',content_type='text/plain',options='Content-Encoding:gzip',retry_params=write_retry_params)
            gcs_file.write(filecontent)
            gcs_file.close()
            filename = None
            filecontent = None
            filelength = None
            write_retry_params = None
            print("file written to GCS");

        except Exception:
            ch = 2
#Adding Url Mapping for various operations in the application
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/findAll',FindALLFiles),
    ('/download',downloadFiles),
    ('/asynchRequest', TestPage),
], debug=True)
