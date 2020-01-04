import psycopg2, sys, datetime, os, getopt
from Roomba import Roomba

def usage():
    print '''
Usage: %s -h HOSTNAME -s SCHEMA -u USERNAME -p PASSWORD command [arguments ...]

FLAGS
    -h|--hostname HOSTNAME
    -s|--schema SCHEMA
    -u|--user USERNAME
    -p|--pass PASSWORD
    -?|--help

COMMANDS
    report [ report_type [ arguments ] ]
        Report Types: [default: threshold]
            - threshold
                Produces a table showing predicted stats for pg-roomba runs with various thresholds. You can override
                these thresholds by supplying a comma-delimited list.
                [ Default: .01,.05,.1,.25,.5,.75 ]  
            - threshold_detail
                Produces a table showing predicted per-table stats for a pg-roomba run for a given threshold.
                [ Default: .1 ]
        
        Note: All values are in kB unless otherwise noted.
    
    run [ threshold [ "dry" ] ]
        - Specify a threshold to override the default of 0.1.
        - Specify a threshold AND the keyword "dry" to output SQL statements without running them.
'''% sys.argv[0]

#set defaults
psql_config = {
    'host': None,
    'schema': None,
    'user': None,
    'pass': None
}

# parse args
options, command_args = getopt.getopt(
    sys.argv[1:],
    'h:s:u:p:t:?',
    ['host', 'schema', 'user', 'pass', 'threshold', 'help']
)

for opt, arg in options:
    if opt in   ('-h', '--host'):
        psql_config['host'] = arg
    elif opt in ('-s', '--schema'):
        psql_config['schema'] = arg
    elif opt in ('-u', '--user'):
        psql_config['user'] = arg
    elif opt in ('-p', '--pass'):
        psql_config['pass'] = arg
    elif opt in ('-?', '--help'):
        usage()
        sys.exit(0)

# check args
error = False
if psql_config['host'] is None:
    error = True
    print 'host is not defined.'
if psql_config['schema'] is None:
    error = True
    print 'schema is not defined.'
if psql_config['user'] is None:
    error = True
    print 'user is not defined.'
if psql_config['pass'] is None:
    error = True
    print 'password is not defined.'
if error:
    usage()
    sys.exit(1)

# set up connection
psql = psycopg2.connect(
    host     = psql_config['host'],
    database = psql_config['schema'],
    user     = psql_config['user'],
    password = psql_config['pass']
)
r = Roomba(psql)

if not command_args:
    raise Exception('No command specified')

elif command_args[0] == 'report':
    if len(command_args) < 2:
        r.threshold_report()
    elif command_args[1] == 'threshold':
        if len(command_args) >= 3:
            r.threshold_report(map(float, command_args[2].split(',')))
        else:
            r.threshold_report()
    elif command_args[1] == 'threshold_detail':
        if len(command_args) >= 3:
            r.threshold_detail_report(float(command_args[2]))
        else:
            r.threshold_detail_report()
    else:
        raise Exception('Unknown report type')

elif command_args[0] == 'run':
    dry = False
    if len(command_args) >= 3:
        if command_args[2].lower() == 'dry':
            dry = True
    if len(command_args) >= 2:
        r.run(threshold=float(command_args[1]), dry=dry)
    else:
        r.run(dry=dry)

else:
    raise Exception('Invalid command "%s"' % command_args[0])
