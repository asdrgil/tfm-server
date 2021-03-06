from app import app, db, socketio
from app.constants import host, port, urlPrefix
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from flask_assets import Environment

if __name__ == '__main__':
    CSSPATH = ""

    assets = Environment(app)

    assets.register('mainCss', \
        'css/own.css', 'css/vendor/bulmaV201911011043.css', 'css/vendor/nestV3.2.0.css', \
        'css/vendor/notyV3.2.0.css', output='cached.css', filters='cssmin')

    assets.register('mainJs', \
        'js/own.js', 'js/vendor/fontAwesomeV5.3.1.js', 'js/vendor/jQueryV3.4.1.js', \
        'js/vendor/notyV3.2.0.js', 'js/vendor/socketIOV1.3.5.js', \
        output='cached2.js', filters='jsmin')

    ################################################################################################################

    assets.register('accordionMultiselectCss', \
        'css/vendor/multipleSelectV1.5.0.css', \
        output='cached3.css', filters='cssmin')

    assets.register('accordionMultiselectJs', \
        'js/vendor/bulmaAccordionV2.0.1.js', 'js/vendor/multipleSelectV1.5.0.js', \
        output='cached4.js', filters='jsmin')

    assets.register('highchartsJs', \
        'js/vendor/highstockV8.0.0.js', 'js/vendor/highstockExportingV8.0.0.js',
        output='cached5.js', filters='jsmin')
        
        #Add url prefix to all urls
    app.wsgi_app = DispatcherMiddleware( 
           app.wsgi_app,
           {urlPrefix: app}
    )

    socketio.run(app, debug=False, host=host, port=port)
