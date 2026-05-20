#!/usr/bin/env bash
# _schema_v1.sh — Schema v1 column positions for all four metric families.
#
# Sourced by every calc in calc/. Never hardcode column positions in a calc;
# always reference the variables defined here.
#
# When the schema version bumps, this file is updated AND every conversion
# script is updated AND every calc is verified against its golden test, in
# the same commit. See maintain/procedures/bump_schema.md.

# Operational schema (data/metrics/operational/{id}.csv)
export COL_DATE=1
export COL_FACILITY=2
export COL_UNITS=3
export COL_CPH=4
export COL_ERROR_RATE=5
export COL_HOURS_RUN=6

# Input schema (data/metrics/inputs/{id}.csv) — placeholder until phase 8
export COL_IN_DATE=1
export COL_IN_FACILITY=2
export COL_IN_HEADCOUNT_TOTAL=3
export COL_IN_HEADCOUNT_NEW=4
export COL_IN_HEADCOUNT_SHIFT1=5
export COL_IN_HEADCOUNT_SHIFT2=6
export COL_IN_HEADCOUNT_SHIFT3=7
export COL_IN_INBOUND_UNITS=8
export COL_IN_ORDER_MIX_COMPLEX=9

# Exception schema (data/metrics/exceptions/{id}.csv) — placeholder until phase 8
export COL_EX_DATE=1
export COL_EX_FACILITY=2
export COL_EX_DAMAGE=3
export COL_EX_MISSORT=4
export COL_EX_MISPICK=5
export COL_EX_LOST=6
export COL_EX_LATE_PICK=7

# Equipment schema (data/metrics/equipment/{id}.csv) — placeholder until phase 8
export COL_EQ_DATE=1
export COL_EQ_FACILITY=2
export COL_EQ_CONVEYOR_DOWN_M=3
export COL_EQ_MHE_DOWN_M=4
export COL_EQ_WMS_INCIDENTS=5
export COL_EQ_SCANNER_FAULTS=6

# Schema version metadata
export SCHEMA_VERSION=v1

# col_for <family> <metric> — resolve a metric name within a family to its
# 1-based column index. Echoes the column number and returns 0 on success;
# returns 1 (and echoes nothing) for an unknown family/metric pair.
#
# This is the single resolver every multi-family calc uses so that adding a
# metric is a one-line change here, not a change in every calc.
col_for() {
    case "$1:$2" in
        operational:units)            echo "$COL_UNITS" ;;
        operational:cph)              echo "$COL_CPH" ;;
        operational:error_rate)       echo "$COL_ERROR_RATE" ;;
        operational:hours_run)        echo "$COL_HOURS_RUN" ;;
        inputs:headcount_total)       echo "$COL_IN_HEADCOUNT_TOTAL" ;;
        inputs:headcount_new)         echo "$COL_IN_HEADCOUNT_NEW" ;;
        inputs:headcount_shift1)      echo "$COL_IN_HEADCOUNT_SHIFT1" ;;
        inputs:headcount_shift2)      echo "$COL_IN_HEADCOUNT_SHIFT2" ;;
        inputs:headcount_shift3)      echo "$COL_IN_HEADCOUNT_SHIFT3" ;;
        inputs:inbound_units)         echo "$COL_IN_INBOUND_UNITS" ;;
        inputs:order_mix_complex)     echo "$COL_IN_ORDER_MIX_COMPLEX" ;;
        exceptions:damage)            echo "$COL_EX_DAMAGE" ;;
        exceptions:missort)           echo "$COL_EX_MISSORT" ;;
        exceptions:mispick)           echo "$COL_EX_MISPICK" ;;
        exceptions:lost)              echo "$COL_EX_LOST" ;;
        exceptions:late_pick)         echo "$COL_EX_LATE_PICK" ;;
        equipment:conveyor_down_m)    echo "$COL_EQ_CONVEYOR_DOWN_M" ;;
        equipment:mhe_down_m)         echo "$COL_EQ_MHE_DOWN_M" ;;
        equipment:wms_incidents)      echo "$COL_EQ_WMS_INCIDENTS" ;;
        equipment:scanner_faults)     echo "$COL_EQ_SCANNER_FAULTS" ;;
        *) return 1 ;;
    esac
}

# worse_direction <family> <metric> — echo "min" if a lower value is worse for
# this metric, "max" if a higher value is worse. Used by worst_day.sh to pick
# a sensible default the user can still override with --direction.
#   operational: cph/units/hours_run → min (less is worse); error_rate → max
#   exceptions/equipment: always max (more failures/downtime is worse)
#   inputs: max by convention, but callers should pass --direction explicitly
worse_direction() {
    case "$1:$2" in
        operational:cph|operational:units|operational:hours_run) echo "min" ;;
        operational:error_rate) echo "max" ;;
        exceptions:*|equipment:*) echo "max" ;;
        *) echo "max" ;;
    esac
}
