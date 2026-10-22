"""Render every section x toggle x a sector with Streamlit AppTest; fail on any exception. Also checks the app never reads the parquet."""
import warnings; warnings.filterwarnings('ignore')
from streamlit.testing.v1 import AppTest
src = open('app/streamlit_app.py').read(); assert 'parquet' not in src.replace('never the parquet', '') and 'processed' not in src
pages = ['Overview', 'Attention around IPO day', 'Does attention predict returns?', 'Pop drives attention', 'By sector', 'Company size', 'Methods & limitations']
for inc in (True, False):
    for sector in ('All', 'Health Care'):
        for p in pages:
            at = AppTest.from_file('../app/streamlit_app.py', default_timeout=60).run()
            at.sidebar.toggle[0].set_value(inc); at.sidebar.selectbox[0].set_value(sector); at.sidebar.radio[0].set_value(p); at.run()
            assert not at.exception, (inc, sector, p, at.exception)
for inc in (True, False):
    at = AppTest.from_file('../app/streamlit_app.py', default_timeout=60).run()
    at.sidebar.toggle[0].set_value(inc); at.sidebar.radio[0].set_value('Company size'); at.run()
    assert not at.exception, ('Company size', inc, at.exception)
    sup = any('suppressed (n<15)' in str(x.value) for x in at.markdown) or any('suppressed' in df.value.to_string() for df in at.dataframe)
    assert sup == (not inc), ('micro suppression should appear only when no-article firms are excluded', inc)
print('APP PASS', 2 * 2 * len(pages), 'renders')
