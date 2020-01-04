import math, time
from . import Query

class Roomba:
    def __init__(self, psql):
        self.psql = psql
        self.psql.autocommit = True
        self._stats_cache = None

    def _convert_size(self, size_bytes):
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return "%s %s" % (s, size_name[i])

    def _get_table_stats(self):
        if self._stats_cache is None:
            # with open('waste.sql', 'r') as fh:
            #     query = fh.read()
            query = Query.get_query()

            p_cur = self.psql.cursor()
            p_cur.execute(query)
            self._stats_cache = p_cur.fetchall()
            p_cur.close()
        return self._stats_cache

    def threshold_detail_report(self, threshold=0.1):
        print "%30s | %40s | %12s | %12s | %12s | %7s | %12s | %12s" % (
        'schema', 'table', 'size', 'wasted', 'unwasted', '%waste', 'gain', 'consumption')
        print "-" * 158

        gain = 0
        overconsumption = 0
        rewrite = 0
        for (schema, table, size, wasted, unwasted) in self._get_table_stats():
            if size == 0:
                continue
            if wasted / size < threshold:
                continue
            consumption = gain - unwasted
            if consumption < overconsumption:
                overconsumption = consumption
            rewrite = rewrite + unwasted
            print "%30s | %40s | %12d | %12d | %12d | %7.2f | %12d | %12d" % (
            schema, table, size/1024, wasted/1024, unwasted/1024, wasted / size * 100, gain/1024, consumption/1024)
            gain = gain + wasted

        print "\nRoomba would require %s free space before running, rewrite %s of table data, and free up %s of disk space." % tuple(
            map(self._convert_size, map(int, [overconsumption * -1, rewrite, gain])))

    def threshold_report(self, thresholds=[0.01, 0.05, 0.10, 0.25, 0.50, 0.75]):
        print "%5s %10s %10s %10s" % ('Thold', 'Need', 'Write', 'Freed')
        for threshold in thresholds:
            gain = 0
            overconsumption = 0
            rewrite = 0
            for (schema, table, size, wasted, unwasted) in self._get_table_stats():
                if wasted / size < threshold:
                    continue
                consumption = gain - unwasted
                if consumption < overconsumption:
                    overconsumption = consumption
                rewrite = rewrite + unwasted
                gain = gain + wasted
            print "%5.2f %10s %10s %10s" % ( tuple([ threshold ]) + tuple(map(self._convert_size, map(int, [overconsumption * -1, rewrite, gain]))) )

    def run(self, threshold=0.1, dry=False):
        cursor = self.psql.cursor()
        for (schema, table, size, wasted, unwasted) in self._get_table_stats():
            if wasted / size < threshold:
                continue
            query = 'VACUUM FULL ANALYZE "%s"."%s";' % (schema, table)
            print '%s' % query
            if not dry:
                prev = time.time()
                cursor.execute(query)
                cur = time.time()
                print "  %6.2f seconds" % (cur-prev)
        cursor.close()
