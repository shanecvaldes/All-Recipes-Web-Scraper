from bs4 import BeautifulSoup, SoupStrainer
import threading
import psycopg2
import time
import asyncio
import aiohttp



class web_scraper:
    def __init__(self):
        # locks
        self.db_connection_lock = threading.RLock()
        self.queue_lock = threading.RLock()
        self.recipe_lock = threading.RLock()
        self.category_lock = threading.RLock()

        # db_connection semaphore
        self.queue_semaphore = threading.Semaphore(1)

        # global variables
        self.ORIGINAL_LINK = 'https://www.allrecipes.com/'
        self.original_links = ['https://www.allrecipes.com/', 'https://www.allrecipes.com/recipes']
        self.link_queue = []
        self.response_dict = {}
        self._flag = True
    
        # ids
        self.recipe_id = 1
        self.category_id = -1

        # times
        self.update_times = []
        self.insert_times = []
        self.find_links_times = []
        self.sift_links_times = []
        self.main_time = []
        self.request_time = []
        self.title_time = []

    async def fetch_many(self, urls):
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch(session, url) for url in urls]
            responses = await asyncio.gather(*tasks)
        return responses

    async def fetch(self, session, url):
        async with session.get(url) as response:
            return await response.text()
    
    async def start_fetching(self, partitioned_list):
        return await self.fetch_many(partitioned_list)
    
    def thread_request(self, partitioned_list):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        thread_reponses = loop.run_until_complete(self.start_fetching(partitioned_list))
        self.queue_lock.acquire()
        self.response_dict.update(dict(zip(partitioned_list, thread_reponses)))
        self.queue_lock.release()
        # loop.close()

    def start_thread_requests(self, num_threads):
        partitions = len(self.link_queue) // num_threads
        threads = []
        if len(self.link_queue) <= num_threads or num_threads == 1:
            self.thread_request(self.link_queue)
        else:
            for j in range(0, num_threads-1):
                threads.append(threading.Thread(target=self.thread_request, args=[self.link_queue[j*partitions:(j*partitions)+partitions]]))
            threads.append(threading.Thread(target=self.thread_request, args=[self.link_queue[(num_threads-1)*partitions::]]))
            for j in range(num_threads):
                threads[j].start()
                threads[j].join()

    def start_thread_scraping(self, num_threads, db_connection):
        threads = []
        for j in range(num_threads):
            threads.append(threading.Thread(target=self.link_scrapper, args=[db_connection.cursor()]))
            threads[j].start()
        for j in range(num_threads):
            threads[j].join()
        
    def init_queue(self, db_cursor):
        # initial queue contains all category links
        db_cursor.execute(f'SELECT link FROM CATEGORIES WHERE parent_id = -1 UNION SELECT link FROM RECIPES WHERE category_id = -1;')
        temp = db_cursor.fetchall()
        max_length = 500
        while len(temp) > 0 and len(self.link_queue) < max_length:
            self.link_queue.append(temp.pop(0)[0])
        self.queue_semaphore = threading.Semaphore(len(self.link_queue))

    def complete_data(self, num_threads, db_connection):
        i = 1
        while len(self.link_queue) > 0:
            print(f'Completing data for {i} time, {len(self.link_queue)} requested.')
            start = time.time()
            self.start_thread_requests(num_threads)
            end = time.time()
            self.request_time.append(end - start)
            self.start_thread_scraping(num_threads, db_connection)
            i += 1
        return

    def start(self):
        #db_connection connection
        db_name = ''
        db_password = ''
        while True:
            db_password = input('Please input db password: ')
            db_name = input('Please input db name: ')
            try:
                db_connection = psycopg2.connect(database=db_name, user='postgres', password=db_password, host='localhost')
                break 
            except:
                print('Failed connection, try again.')
                continue
        db_cursor = db_connection.cursor()
        # initialize ids
        db_cursor.execute(f'''SELECT MAX(id) FROM categories;''')
        result = db_cursor.fetchall()[0][0]
        if result != None:
            self.category_id = int(result) + 1

        db_cursor.execute(f'''SELECT MAX(id) FROM recipes;''')
        result = db_cursor.fetchall()[0][0]
        if result != None:
            self.recipe_id = int(result) + 1
        
        num_threads = int(input('How many scraper threads for this run? '))
        if num_threads <= 0:
            print('Number of threads must be more than 0. Please re-run program')
            return
        iterations = 0
        while True:
            try:
                iterations = int(input('How many cycles will be ran?'))
                if iterations <= 0:
                    print('Invlalid input, please try again.')
                    continue
                break
            except:
                print('Invlalid input, please try again.')

        if iterations <= 0:
            print('Number of iterations must be more than 0. Please re-run program')
            return
        
        self.init_queue(db_cursor)
        for i in range(iterations):
            self.init_queue(db_cursor)
            # partition queue for threads
            print(f'Starting request {i}: Requesting {len(self.link_queue)} urls')
            start = time.time()
            self.start_thread_requests(num_threads)
            end = time.time()
            print(f'Request {i} ended')
            self.request_time.append(end - start)
            self.start_thread_scraping(num_threads, db_connection)

        # UNCOMMENT HERE
        # self._flag = False
        # print('Completing data')
        # self.complete_data(num_threads, db_connection)
            
        db_connection.commit()
        db_connection.close()

        print(f'Update avg: {sum(self.update_times) / len(self.update_times)}')
        print(f'Insert avg: {sum(self.insert_times) / len(self.insert_times)}')
        print(f'Find all avg: {sum(self.find_links_times) / len(self.find_links_times)}')
        print(f'For loop avg: {sum(self.sift_links_times) / len(self.sift_links_times)}')
        print(f'Main time avg: {sum(self.main_time) / len(self.main_time)}')
        print(f'Request time avg: {sum(self.request_time) / len(self.request_time)}')
        print(f'Title find time avg: {sum(self.title_time) / len(self.title_time)}')


        print('Finished')

    def link_scrapper(self, cursor):
        # cycle through every available link
        title_strainer = SoupStrainer('h1', class_='comp mntl-taxonomysc-heading mntl-text-block')
        link_strainer = SoupStrainer('a')
        while self.queue_semaphore.acquire(blocking=False):
            start_main = time.time()

            self.queue_lock.acquire(blocking=True)
            print(len(self.response_dict))
            # CRITICAL SECTION
            temp = self.link_queue.pop(0)
            # END CRITICAL
            self.queue_lock.release()

            current_link = temp
            try:
                html = self.response_dict.pop(temp)
            except:
                continue
    
            # find all links on a given page
            start = time.time()
            links = BeautifulSoup(html, 'html.parser', parse_only=link_strainer)
            valid_links = [a for a in links if a.get('href') != None and self.ORIGINAL_LINK in a.get('href')]
            end = time.time()
            self.find_links_times.append(end-start)

            # initialize the default parent/category id
            closest_parent = ''
            breadcrumb_id = -1
            start_links = time.time()
            for a in valid_links:
                href = a.get('href')
                class_id = a.get('class')

                is_new_link_recipe = '/recipe/' in href or '-recipe-' in href
                is_new_link_category = '/recipes/' in href
                if is_new_link_category == is_new_link_recipe == False:
                    continue
                
                # use breadcrumb to find category hierarchy
                is_breadcrumb = class_id != None and ' mntl-breadcrumbs__link' in ' '.join(class_id)
            
                # use the largest breadcrumb in hierarchy
                if is_breadcrumb and is_new_link_category and len(closest_parent) < len(href):
                    closest_parent = href
                
                # insert recipe as long as main sleeps
                start = time.time()
                if is_new_link_recipe and self._flag:
                    # print('this works')
                    self.recipe_lock.acquire()
                    # CRITICAL SECTION
                    cursor.execute(f'''SELECT \'{href}\' FROM RECIPES WHERE \'{href}\' = link''')
                    result = cursor.fetchall()
                    unique = len(result) == 0
                    # add to table when unique
                    if unique == False:
                        self.recipe_lock.release()
                        continue
                    else:
                        self.insert_recipe_db_connection(href, cursor)
                        self.link_queue.append(href)
                    # END CRITICAL
                    self.recipe_lock.release()
                # insert category as long as main sleeps OR is breadcrumb
                elif is_new_link_category:
                    self.category_lock.acquire()
                    # CRITICAL CHECK
                    cursor.execute(f'''SELECT link, id FROM CATEGORIES WHERE \'{href}\' = link''')
                    result = cursor.fetchall()
                    unique = len(result) == 0
                    # add to table when unique and when flag is false OR when unique and is breadcrumb
                    if unique == False:
                        temp = result[0][-1]
                    else:
                        temp = self.insert_category_db_connection(href, cursor)
                        self.link_queue.append(href)

                    if closest_parent == href:
                        breadcrumb_id = temp

                    # END CRITICAL
                    self.category_lock.release()
                end = time.time()
                self.insert_times.append(end - start)
            end_links = time.time()
            self.sift_links_times.append(end_links - start_links)
            
            # avoid the default links
            if current_link in self.original_links:
                continue

            # look for the title of the page
            # current_title = soup.find_all('h1', class_='comp mntl-taxonomysc-heading mntl-text-block')
            start = time.time()
            current_title = BeautifulSoup(html, 'html.parser', parse_only=title_strainer)
            if len(current_title) != 0:
                current_title = current_title.text
            current_title = self.removePuncuation(current_title)
            end = time.time()
            self.title_time.append(end - start)

            # update information on current link
            is_curr_link_recipe = '/recipe/' in current_link or '-recipe-' in current_link
            is_curr_link_category = '/recipes/' in current_link
            start = time.time()
            if is_curr_link_category:
                self.update_category(current_link, cursor, breadcrumb_id, current_title)
            elif is_curr_link_recipe:
                self.update_recipe(current_link, cursor, breadcrumb_id, current_title)
            end = time.time()
            self.update_times.append(end - start)
            self.main_time.append(end - start_main)

            # print(self.breadcrumb_relationships[current_link], current_link, len(self.link_queue))
        print('Web Scaper Released')

    def insert_category_db_connection(self, link, cursor):
        result = self.category_id
        cursor.execute(f'''INSERT INTO categories(link, id) VALUES (\'{link}\', {self.category_id}) ON CONFLICT DO NOTHING;''')
        self.category_id += 1
        return result
        
    def insert_recipe_db_connection(self, link, cursor):
        result = self.recipe_id
        cursor.execute(f'''INSERT INTO recipes(link, id) VALUES (\'{link}\', {self.recipe_id}) ON CONFLICT DO NOTHING;''')
        self.recipe_id += 1
        return result
    
    def update_recipe(self, link, cursor, category_id=-1, title=''):
        cursor.execute(f'''UPDATE RECIPES SET category_id = {category_id}, title = \'{title}\' WHERE link = \'{link}\'''')
        return
    
    def update_category(self, link, cursor, parent_id=-1, title=''):
        cursor.execute(f'''UPDATE CATEGORIES SET parent_id = {parent_id}, title = \'{title}\' WHERE link = \'{link}\'''')
        return
    
    def removePuncuation(self, s):
        punc = '''!()-[]{};:'"\,<>./?@#$%^&*_~`'''
        result = ''
        for ele in s:
            if ele not in punc:
                result += ele
        return result

def main():
    current_run = web_scraper()
    current_run.start()

    

main()