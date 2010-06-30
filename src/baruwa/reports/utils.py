from django.utils import simplejson
from django.db.models import Count, Sum, Q
from baruwa.reports.forms import FilterForm,FILTER_ITEMS,FILTER_BY
from baruwa.messages.models import Message
from baruwa.utils.misc import to_dict, apply_filter

pie_colors = ['#FF0000','#ffa07a','#deb887','#d2691e','#008b8b','#006400','#ff8c00','#ffd700','#f0e68c','#000000']

def pack_json_data(data, arg1, arg2):
    rv = []

    n = 0
    for item in data:
        pie_data = {}
        pie_data['y'] = item[arg2]
        pie_data['color'] = pie_colors[n]
        pie_data['stroke'] = 'black'
        pie_data['tooltip'] = item[arg1]
        rv.append(pie_data)
        n += 1
    return simplejson.dumps(rv)
  
def run_hosts_query(request, active_filters):
    data = Message.messages.for_user(request).values('clientip').filter(clientip__isnull=False).exclude(clientip = '').annotate(num_count=Count('clientip'),
        size=Sum('size'),virus_total=Sum('virusinfected'),spam_total=Sum('spam')).order_by('-num_count')
    data = apply_filter(data,request,active_filters)
    data = data[:10]
    return data
        
def run_query(query_field, exclude_kwargs, order_by, request, active_filters):
    data = Message.messages.for_user(request).values(query_field).\
    exclude(**exclude_kwargs).annotate(num_count=Count(query_field),size=Sum('size')).order_by(order_by)
    data = apply_filter(data,request,active_filters)
    data = data[:10]
    return data

def format_totals_data(rows):
    data = []
    dates = []
    mail_total = []
    spam_total = []
    virus_total = []
    for i in range(len(rows)):
        date = "%s" % rows[i][0]
        total = int(rows[i][1])
        virii = int(rows[i][2])
        spam = int(rows[i][3])
        vpercent = "%.1f" % ((1.0 * virii/total)*100)
        spercent = "%.1f" % ((1.0 * spam/total)*100)
        mail_total.append(total)
        spam_total.append(spam)
        virus_total.append(virii)
        dates.append(date)
        data.append({'date':date,'count':total,'virii':virii,'vpercent':vpercent,'spam':spam,'spercent':spercent,'size':int(rows[i][4])})
    return mail_total, spam_total, virus_total, dates, data

def format_sa_data(rows):
    counts = []
    scores = []
    data = []
    for i in range(len(rows)):
        score = "%s" % rows[i][0]
        count = int(rows[i][1])
        counts.append(count)
        scores.append(score)
        data.append({'score':score,'count':count})
    return counts, scores, data

def gen_dynamic_raw_query(filter_list,active_filters=None):
    filter_items = to_dict(list(FILTER_ITEMS))
    filter_by = to_dict(list(FILTER_BY))
    sql = []
    vals = []
    asql = []
    avals = []
    osql = []
    ovals = []
    nosql = []
    novals = []
    for filter_item in filter_list:
        if filter_item['filter'] == 1:
            tmp = "%s = %%s" % filter_item['field']
            if tmp in asql:
                ix = asql.index(tmp)
                tv = avals[ix]

                osql.append(asql[ix])
                ovals.append(tv)

                asql.remove(tmp)
                avals.remove(tv)

                osql.append(tmp)
                ovals.append(filter_item['value'])
            else:
                if tmp in osql:
                    osql.append(tmp)
                    ovals.append(filter_item['value'])
                else:
                    asql.append(tmp)
                    avals.append(filter_item['value'])
        if filter_item['filter'] == 2:
            tmp = "%s != %%s" % filter_item['field']
            if tmp in asql:
                ix = asql.index(tmp)
                tv = avals[ix]

                nosql.append(asql[ix])
                novals.append(tv)

                asql.remove(tmp)
                avals.remove(tv)

                nosql.append(tmp)
                novals.append(filter_item['value'])
            else:
                if tmp in nosql:
                    nosql.append(tmp)
                    novals.append(filter_item['value'])
                else:
                    asql.append(tmp)
                    avals.append(filter_item['value'])
        if filter_item['filter'] == 3:
            tmp = "%s > %%s" % filter_item['field']
            if tmp in asql:
                ix = asql.index(tmp)
                tv = avals[ix]

                osql.append(asql[ix])
                ovals.append(tv)

                asql.remove(tmp)
                avals.remove(tv)

                osql.append(tmp)
                ovals.append(filter_item['value'])
            else:
                if tmp in osql:
                    osql.append(tmp)
                    ovals.append(filter_item['value'])
                else:
                    asql.append(tmp)
                    avals.append(filter_item['value'])
        if filter_item['filter'] == 4:
            tmp = "%s < %%s" % filter_item['field']
            if tmp in asql:
                ix = asql.index(tmp)
                tv = avals[ix]

                osql.append(asql[ix])
                ovals.append(tv)

                asql.remove(tmp)
                avals.remove(tv)

                osql.append(tmp)
                ovals.append(filter_item['value'])
            else:
                if tmp in osql:
                    osql.append(tmp)
                    ovals.append(filter_item['value'])
                else:
                    asql.append(tmp)
                    avals.append(filter_item['value'])
        if filter_item['filter'] == 5:
            tmp = "%s LIKE %%s" % filter_item['field']
            if tmp in asql:
                ix = asql.index(tmp)
                tv = avals[ix]

                osql.append(asql[ix])
                ovals.append(tv)

                asql.remove(tmp)
                avals.remove(tv)

                osql.append(tmp)
                ovals.append(filter_item['value'])
            else:
                if tmp in osql:
                    osql.append(tmp)
                    ovals.append(filter_item['value'])
                else:
                    asql.append(tmp)
                    avals.append('%'+filter_item['value']+'%')
        if filter_item['filter'] == 6:
            tmp = "%s NOT LIKE %%s" % filter_item['field']
            if tmp in asql:
                ix = asql.index(tmp)
                tv = avals[ix]

                nosql.append(asql[ix])
                novals.append(tv)

                asql.remove(tmp)
                avals.remove(tv)

                nosql.append(tmp)
                novals.append(filter_item['value'])
            else:
                if tmp in nosql:
                    nosql.append(tmp)
                    novals.append(filter_item['value'])
                else:
                    asql.append(tmp)
                    avals.append('%'+filter_item['value']+'%')
        if filter_item['filter'] == 7:
            tmp = "%s REGEXP %%s" % filter_item['field']
            if tmp in asql:
                ix = asql.index(tmp)
                tv = avals[ix]

                osql.append(asql[ix])
                ovals.append(tv)

                asql.remove(tmp)
                avals.remove(tv)

                osql.append(tmp)
                ovals.append(filter_item['value'])
            else:
                if tmp in osql:
                    osql.append(tmp)
                    ovals.append(filter_item['value'])
                else:
                    asql.append(tmp)
                    avals.append(filter_item['value'])
        if filter_item['filter'] == 8:
            tmp = "%s NOT REGEXP %%s" % filter_item['field']
            if tmp in asql:
                ix = asql.index(tmp)
                tv = avals[ix]

                nosql.append(asql[ix])
                novals.append(tv)

                asql.remove(tmp)
                avals.remove(tv)

                nosql.append(tmp)
                novals.append(filter_item['value'])
            else:
                if tmp in nosql:
                    nosql.append(tmp)
                    novals.append(filter_item['value'])
                else:
                    asql.append(tmp)
                    avals.append(filter_item['value'])
        if filter_item['filter'] == 9:
            tmp = "%s IS NULL" % filter_item['field']
            sql.append(tmp)
        if filter_item['filter'] == 10:
            tmp = "%s IS NOT NULL" % filter_item['field']
            sql.append(tmp)
        if filter_item['filter'] == 11:
            tmp = "%s > 0" % filter_item['field']
            sql.append(tmp)
        if filter_item['filter'] == 12:
            tmp = "%s = 0" % filter_item['field']
            sql.append(tmp)
        if not active_filters is None:
            active_filters.append({'filter_field':filter_items[filter_item['field']],
                'filter_by':filter_by[int(filter_item['filter'])],'filter_value':filter_item['value']})
    for item in sql:
        asql.append(item)

    andsql = ' AND '.join(asql)
    orsql = ' OR '.join(osql)
    nsql = ' AND '.join(nosql)

    for item in ovals:
        avals.append(item)

    for item in novals:
        avals.append(item)

    if andsql != '':
        if orsql != '':
            if nsql != '':
                sq = andsql + ' AND ( '+orsql+' ) AND ( '+nsql+' )' 
            else:
                sq = andsql + ' AND ( '+orsql+' )'
        else:
            if nsql != '':
                sq = andsql + ' AND ( '+nsql+' )'
            else:
                sq = andsql
    else:
        if orsql != '':
            if nsql != '':
                sq = '( '+orsql+' ) AND ( '+nsql+' )'
            else:
                sq = '( '+orsql+' )'
        else:
            if nsql != '':
                sq = '( '+nsql+' )'
            else:
                sq = ' 1=1 '
    return (sq,avals)