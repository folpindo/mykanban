from setuptools import setup

setup(
    name = 'MyKanban',
    version = '0.0.1',
    packages = ['mykanban'],
    author = 'Faustino Olpindo',
    author_email = 'folpindo@gmail.com',
    description = 'My Kanban Tool',
    keywords = 'kanban',
    url = '',
    install_requires = ['Trac>=0.11', 'Genshi>=0.5', 'Python>=2.5'],
    entry_points = """
        [trac.plugins]
        MyKanban = mykanban
    """,
    package_data={
	'mykanban':[
            'templates/*.html',
            'htdocs/css/*.css',
            'htdocs/js/*.js',
            'htdocs/images/*'
	]
    }
)
