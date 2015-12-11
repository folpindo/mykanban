from genshi.builder import tag
import re
import time
from trac.core import *
from trac.util import Markup
from trac.util import escape
from trac.web.chrome import Chrome
from trac.web.chrome import INavigationContributor
from trac.web.chrome import ITemplateProvider
from trac.web.chrome import add_script
from trac.web.chrome import add_stylesheet
from trac.web.main import IRequestHandler


class Db():
    
    def __init__(self, db):
        self.db = db
        
    def execute_query(self, sql):
        db = self.db
        cursor = db.cursor()
        self.cursor = cursor
        cursor.execute(sql)


class KanbanItem(Db):

    def build_update_str(self, data):
        set_values = None
        kvlist = []
        
        for k, v in data.items():
            i = "%s='%s'" % (k, v)
            kvlist.append(i)
            
        return ",".join(kvlist)
    
    def select(self, fields, criteria):
        f = ",".join(fields)
        crit = self.build_update_str(criteria)
        sql = "SELECT %s FROM kanban_items WHERE %s" % (f, crit)
        self.execute_query(sql)
    
    def insert(self, data):
        sql = "INSERT INTO kanban_items (stack_id,title,rank,added_by) VALUES ('%s','%s','%s','%s')" % (data['stack_id'], data['title'], data['rank'], data['added_by'])
        return self.execute_query(sql)
    
    def update(self, criteria, data):
        data['modified'] = time.time()
        bus = self.build_update_str(data)
        crit = self.build_update_str(criteria)
        sql = "UPDATE kanban_items set %s WHERE %s" % (bus, crit)
        self.execute_query(sql)
        return sql
    
    def delete(self, criteria, soft=False):
        if not soft:
            crit = self.build_update_str(criteria)
            sql = "DELETE FROM kanban_items WHERE %s" % crit
            return self.execute_query(sql)
        else:
            crit = self.build_update_str(criteria)
            data = self.build_update_str({"deleted":1})
            return self.update(crit, data)
    
class MyKanbanPlugin(Component):
    
    implements(INavigationContributor, IRequestHandler, ITemplateProvider)

    def get_active_navigation_item(self, req):
        return 'mykanban'

    def get_navigation_items(self, req):
        yield 'mainnav', 'mykanban', Markup('<a href="%s">MyKanban</a>' % (
                                            self.env.href.mykanban()))

    def match_request(self, req):
        return req.path_info == '/mykanban'

    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]
        
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('mykanban', resource_filename(__name__, 'htdocs'))]
    
    def select_item(self,fields,criteria):
        with self.env.db_transaction as db:
            fields = ['id','stack_id','rank','title']
            criteria = {
                'stack_id':1
            }
            item = KanbanItem(db)
            item.select(fields,criteria)
            stack_cursor = item.cursor
    
    def insert_item(self, data):
        with self.env.db_transaction as db:
            item = KanbanItem(db)
            res = item.insert(data)
    
    def update_item(self, criteria, data):
        with self.env.db_transaction as db:
            item = KanbanItem(db)
            res = item.update(criteria, data)
    
    def delete_item(self, criteria):
        with self.env.db_transaction as db:
            item = KanbanItem(db)
            res = item.delete(criteria)
            
    def update_rank(self, item_id, new_rank):
        with self.env.db_transaction as db:
            
            item = KanbanItem(db)
            
            select_fields = ['stack_id', 'rank']
            select_criteria = {'id':item_id}
            item.select(select_fields, select_criteria)
            
            cursor = item.cursor
            
            stack_id, old_rank = cursor.fetchone()
            
            if new_rank < old_rank:
                return cursor.execute("""
                    UPDATE kanban_items
                    SET rank = rank + 1
                    WHERE stack_id=%s AND rank >= %s AND rank < %s
                """, (stack_id, new_rank, old_rank))
                
            elif new_rank > old_rank:
                return cursor.execute("""
                    UPDATE kanban_items
                    SET rank = rank - 1
                    WHERE stack_id=%s AND rank > %s AND rank <= %s
                """, (stack_id, old_rank, new_rank))

    def process_request(self, req):
        
        add_stylesheet(req, 'mykanban/css/mykanban.css')
        add_script(req, 'mykanban/js/mykanban.js')
        chrome = Chrome(self.env)
        chrome.add_jquery_ui(req)
        process = req.args.get("process")

        item = None
        res = {}
        data = {}
        
        if process == "insert":
            
            with self.env.db_transaction as db:
                
                data = {
                    'stack_id': 3,
                    'title': 'test item 10',
                    'rank': 10,
                    'added_by': 'user',
                    'modified_by': 'user'
                }
                
                item = KanbanItem(db)
                res = item.insert(data)
        
        if process == "update":
            
            with self.env.db_transaction as db:
                
                criteria = {
                    'id':9
                }
                
                data = {
                    'stack_id': 1,
                    'title': 'test item update',
                    'rank': 5,
                    'added_by': 'user',
                    'modified_by': 'user',
                }
                
                item = KanbanItem(db)
                res = item.update(criteria, data)
                    
        if process == "delete":
            
            with self.env.db_transaction as db:
                
                criteria = {
                    'id':1
                }
                
                item = KanbanItem(db)
                res = item.delete(criteria)
                
        if process == "update-rank":
            
            item_id = int(req.args.get("id"))
            new_rank = int(req.args.get("rank"))
            
            ret = self.update_rank(item_id, new_rank)
            
            criteria = {
                'id':item_id
            }
            
            data = {
                'rank': new_rank,
                'modified_by': 'user'
            }
            
            with self.env.db_transaction as db:
                
                item = KanbanItem(db)
                res = item.update(criteria, data)
            
            self.log.debug("update ret:")
            self.log.debug(ret)
            
        data = {}

        data['greeting'] = "Hello world"
        data['listing'] = ["list 1","listt 2"]
        
        stack_cursor = None
        
        with self.env.db_transaction as db:
            
            fields = ['id','stack_id','rank','title']
            
            criteria = {
                'stack_id':1
            }
            
            item = KanbanItem(db)
            item.select(fields,criteria)
            stack_cursor = item.cursor
            
        data['stack_cursor'] = stack_cursor
        
        return 'mykanban.html', data, None
