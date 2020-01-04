# Postgres Roomba

_Slightly_ smarter `VACUUM FULL` for Postgres.

## What does it _do_?

pg-roomba examines your tables and how much 'wasted' space is within them, filters out those below a given percentage of 'waste', and then runs `VACUUM FULL` against them in order of smallest to largest amount of 'unwasted' space.

## What Problems Does this Solve?

1. "My disk is nearly full and a simple `VACUUM FULL` pushes it to 100% and fails."
    - pg-roomba always begins VACUUM-ing the smallest tables first, cumulatively releasing small chunks of disk space which can allow larger and larger tables to successfully be VACUUM-ed.
    - The reporting functions can also give you an estimate of how much free disk space needs to exist to complete the VACUUM process.
2. "I have huge tables that I don't want to process just to release inconsequential amounts of space."
    - You can specify a threshold percentage of "waste" space inside a table, below which pg-roomba will simply skip it.
    - You can also leverage the reporting functionality to manually construct a set of VACUUM statements.
    
## Usage

```
Usage: roomba.py -h HOSTNAME -s SCHEMA -u USERNAME -p PASSWORD command [arguments ...]

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

```

## Reporting

### `threshold`

Example Output:

```
Thold       Need      Write      Freed
 0.01   21.06 GB  111.13 GB   16.28 GB
 0.05   21.84 GB   74.65 GB    15.5 GB
 0.10   27.36 MB   22.35 GB   12.06 GB
 0.25   69.59 MB    13.2 GB    9.37 GB
 0.50  694.96 MB  705.41 MB    2.03 GB
 0.75         0B         0B         0B
```

Columns:
- `Thold`: Threshold
- `Need`: The estimated amount of free space required to run pg-roomba.
- `Write`: The estimated amount of table data that will be re-written during the VACUUM run.
- `Freed`: The estimated amount of disk space that will be freed by the end.

This report can be very useful for planning purposes. As you can see from the above example moving the threshold from 0.10 to 0.05 would more than triple the amount of data to be rewritten, but only release 30% more disk, as well as requiring far more available disk beforehand.

### `threshold_detail`

Example Output:

```
   schema |         table |      size |    wasted |   unwasted |  %waste |    gain |  consumption
-------------------------------------------------------------------------------------------------
    email |      template |        40 |         8 |         32 |   20.00 |       0 |          -32 
    agent |  compensation |      1936 |       240 |       1696 |   12.40 |       8 |        -1688
  contact |      location |     10048 |      1048 |       9000 |   10.43 |     248 |        -8752
   payout |     reporting |    827064 |    111376 |     715688 |   13.47 |    1296 |      -714392
   orders |       summary |   5216392 |   1156472 |    4059920 |   22.17 |  112672 |     -3947248
   
Roomba would require 3.76 GB free space before running, rewrite 4.56 GB of table data, and free up 1.21 GB of disk space.
```

Columns:
- `schema`
- `table`
- `size`: The estimated table size.
- `wasted`: The estimated amount of wasted space inside the table.
- `unwasted`: The estimated amount of non-wasted space inside the table. [This determines the order of execution]
- `%waste`: The percentage of 'wasted' space in the table. [Filtered against the given threshold]
- `gain`: The estimated amount of disk freed by previous operations.
- `consumpton`: `gain - size`, negative values indicate disk requirements beyond what was available at the beginning.

## Caveats

1. Postgres does not have a native capability to report either table size, nor the amount of wasted space within. Both values are _estimations_.
2. Because the above estimations form the basis of the data that this tool runs on there can be significant margins of error in all values.
    - pg-roomba may require more free space prior to a run than was advertised.
    - pg-roomba may not free up as much disk space as advertised.
    - some tables might not shrink at all.
3. If you're low on space it is _quite likely_ that pg-roomba will fill your disk.
    - This tool is a _best effort_, not a magic wand.
    - In the event that your disk fills up during a pg-roomba run it is up to postgres to recover gracefully.
    - _Unless_ your postgres/filesystem/OS config is buggy.
    - Have backups. Proceed with caution.
4. This is still a `VACUUM FULL` operation which will lock the table while it runs. Do not use it on a live system without bearing this in mind.

## Credits

The query that generates the size and waste statistics is a combination of:
- [This query](https://wiki.postgresql.org/wiki/Show_database_bloat) from [check_postgres](http://bucardo.org/check_postgres/) to show "wasted space".
- [This query](https://makandracards.com/makandra/52141-postgresql-how-to-show-table-sizes) to show table sizes.