from django.shortcuts import render_to_response, get_object_or_404
from django.views.generic.list_detail import object_list
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse, Http404, HttpResponseRedirect
from django.template import RequestContext
from django.utils import simplejson
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator
from baruwa.messages.models import Message
from baruwa.messages.forms import QuarantineProcessForm
from baruwa.utils.process_mail import search_quarantine, host_is_local, release_mail, \
    parse_email, remote_attachment_download, remote_preview, remote_process, return_attachment
from baruwa.utils.misc import jsonify_msg_list, apply_filter
import re, urllib

@login_required
def index(request, list_all=0, page=1, quarantine=0, direction='dsc', order_by='timestamp'):
    """index"""
    active_filters = []
    ordering = order_by
    if direction == 'dsc':
        ordering = order_by
        order_by = '-%s' % order_by

    if not list_all:
        last_ts = request.META.get('HTTP_X_LAST_TIMESTAMP', None)
        if not last_ts is None:
            last_ts = last_ts.strip()
            if not re.match(r'^(\d{4})\-(\d{2})\-(\d{2})(\s)(\d{2})\:(\d{2})\:(\d{2})$',last_ts):
                last_ts = None
        if not last_ts is None and request.is_ajax():
            message_list = Message.messages.for_user(request).values('id','timestamp','from_address',
            'to_address','subject','size','sascore','highspam','spam','virusinfected','otherinfected',
            'whitelisted','blacklisted','nameinfected','scaned').filter(timestamp__gt=last_ts)[:50]
        else:
            message_list = Message.messages.for_user(request).values('id','timestamp','from_address',
            'to_address','subject','size','sascore','highspam','spam','virusinfected','otherinfected',
            'whitelisted','blacklisted','nameinfected','scaned')[:50]
    else:
        if quarantine:
            message_list = Message.quarantine.for_user(request).values('id','timestamp','from_address',
            'to_address','subject','size','sascore','highspam','spam','virusinfected','otherinfected',
            'whitelisted','blacklisted','isquarantined','nameinfected','scaned').order_by(order_by)
        else:
            message_list = Message.messages.for_user(request).values('id','timestamp','from_address',
            'to_address','subject','size','sascore','highspam','spam','virusinfected','otherinfected',
            'whitelisted','blacklisted','nameinfected','scaned').order_by(order_by)
        message_list = apply_filter(message_list, request, active_filters)

    if request.is_ajax():
        if not list_all:
            message_list = map(jsonify_msg_list, message_list)
            pg = None
        else:
            p = Paginator(message_list,50)
            if page == 'last':
                page = p.num_pages
            po = p.page(page)
            message_list = po.object_list
            message_list = map(jsonify_msg_list, message_list)
            page = int(page)
            quarantine = int(quarantine)
            ap = 2
            sp = max(page - ap, 1)
            if sp <= 3: sp = 1
            ep = page + ap + 1
            pn = [n for n in range(sp,ep) if n > 0 and n <= p.num_pages]
            pg = {'page':page,'pages':p.num_pages,'page_numbers':pn,'next':po.next_page_number(),
            'previous':po.previous_page_number(),'has_next':po.has_next(),'has_previous':po.has_previous(),
            'show_first':1 not in pn,'show_last':p.num_pages not in pn,'quarantine':quarantine,
            'direction':direction,'order_by':ordering}
        json = simplejson.dumps({'items':message_list,'paginator':pg})
        return HttpResponse(json, mimetype='application/javascript')

    if list_all:
        return object_list(request, template_name='messages/index.html', queryset=message_list, 
        paginate_by=50, page=page, extra_context={'quarantine': quarantine,'direction':direction,
        'order_by':ordering,'app':'messages','active_filters':active_filters, 'list_all':list_all},
        allow_empty=True)
    else:
        return object_list(request, template_name='messages/index.html', queryset=message_list, 
        extra_context={'quarantine': quarantine,'direction':direction,'order_by':ordering,
        'app':'messages','active_filters':active_filters, 'list_all':list_all})

@login_required
def detail(request, message_id):
    """
    Displays details of a message
    """
    message_details = get_object_or_404(Message, id=message_id)
    if not message_details.can_access(request):
        return HttpResponseForbidden('You are not authorized to access this page')

    error_list = ''
    quarantine_form = QuarantineProcessForm()
    quarantine_form.fields['message_id'].widget.attrs['value'] = message_details.id

    if request.method == 'POST':
        quarantine_form = QuarantineProcessForm(request.POST)
        success = True
        if quarantine_form.is_valid():
            if not host_is_local(message_details.hostname):
                params = urllib.urlencode(request.POST)
                remote_response = remote_process(message_details.hostname,request.META['HTTP_COOKIE'], message_id, params)
                response = remote_response['response']
                if request.is_ajax():
                    return HttpResponse(response, content_type='application/javascript; charset=utf-8')
                try:
                    r = simplejson.loads(response)
                    if r['success']:
                        success = True
                    else:
                        success = False
                    error_list = r['response']
                except:
                    success = False
                    error_list = 'Error: Empty server response'
            else:
                file_name = search_quarantine(message_details.date, message_id)
                if not file_name is None:
                    if quarantine_form.cleaned_data['release']:
                        # release
                        if quarantine_form.cleaned_data['use_alt']:
                            to_addr = quarantine_form.cleaned_data['altrecipients']
                        else:
                            to_addr = message_details.to_address
                        to_addr = to_addr.split(',')
                        if not release_mail(file_name,to_addr,m.from_address):
                            success = False
                        template = 'messages/released.html'
                        html = render_to_string(template, {'id': message_details.id,'addrs':to_addr,'success':success})
                    if quarantine_form.cleaned_data['salearn']:
                        #salean
                        SALEARN_OPTS = ('spam', 'ham', 'forget')
                        template = "messages/salearn.html"
                        salearn = int(quarantine_form.cleaned_data['salearn_as'])
                        if salearn <= 2:
                            status = sa_learn(file_name, SALEARN_OPTS[salearn])
                            if not status['success']:
                                success = False
                            html = render_to_string(template, {'id': message_details.id,'msg':status['output'],'success':success})
                        else:
                            success = False
                            html = 'Invalid salearn options supplied'
                    if quarantine_form.cleaned_data['todelete']:
                        #delete
                        import os
                        if os.path.exists(file_name):
                            try:
                                os.remove(file_name)
                                message_details.quarantined = 0
                                message_details.save()
                            except:
                                success = False
                                pass
                        template = "messages/delete.html"
                        html = render_to_string(template, {'id': message_details.id,'success':success})
                else:
                    html = 'The quarantined file could not be processed'
                    success = False
        else:
            error_list = quarantine_form.errors.values()[0]
            error_list = error_list[0]
            html = error_list
            success = False
        if request.is_ajax():
            response = simplejson.dumps({'success':success,'html': html})
            return HttpResponse(response, content_type='application/javascript; charset=utf-8')

    quarantine_form.fields['altrecipients'].widget.attrs['size'] = '55'
    return render_to_response('messages/detail.html', locals(), context_instance=RequestContext(request))

@login_required
def preview(request, message_id, is_attach=False, attachment_id=0):
    """
    Returns a message preview of a quarantined message, depending on
    the call it returns XHTML or JSON
    """
    message_details = get_object_or_404(Message, id=message_id)
    if not message_details.can_access(request):
        return HttpResponseForbidden('You are not authorized to access this page')

    if host_is_local(message_details.hostname):
        file_name = search_quarantine(message_details.date, message_id)
        if not file_name is None:
            try:
                import email
                fp = open(file_name)
                msg = email.message_from_file(fp)
                fp.close()
                if is_attach:
                    message = return_attachment(msg, attachment_id)
                    if message:
                        import base64
                        attachment_data = message.getvalue()
                        ct = message.content_type
                        if request.is_ajax():
                            json = simplejson.dumps({'success':True, 'attachment':base64.encodestring(attachment_data), 
                            'mimetype':ct, 'name':message.name})
                            response = HttpResponse(json, content_type='application/javascript; charset=utf-8')
                            message.close()
                            return response
                        response = HttpResponse(attachment_data, mimetype=ct)
                        response['Content-Disposition'] = 'attachment; filename=%s' % message.name
                        message.close()
                        return response
                    else:
                        raise Http404
                else:
                    message = parse_email(msg)
                if request.is_ajax():
                    response = simplejson.dumps({'message':message,'message_id':message_details.id})
                    return HttpResponse(response, content_type='application/javascript; charset=utf-8')
                return render_to_response('messages/preview.html', {'message':message,'message_id':message_details.id},
                    context_instance=RequestContext(request))
            except:
                raise Http404
        else:
            raise Http404
    else:
        #remote
        if is_attach:
            remote_response = remote_attachment_download(message_details.hostname, request.META['HTTP_COOKIE'], message_id, attachment_id)
            if remote_response['success']:
                import base64
                data = remote_response['response']
                attach = simplejson.loads(data)
                if attach['success']:
                    attachment_data = base64.decodestring(attach['attachment'])
                    ct = attach['mimetype']
                    response = HttpResponse(attachment_data, mimetype=ct)
                    response['Content-Disposition'] = 'attachment; filename=%s' % attach['name']
                    return response
            raise Http404
        else:
            remote_response = remote_preview(message_details.hostname, request.META['HTTP_COOKIE'], message_id)
            if remote_response['success']:
                data = remote_response['response']
                items = simplejson.loads(data)
                message = items['message']

                if request.is_ajax():
                    response = simplejson.dumps({'message':message, 'message_id':message_id})
                    return HttpResponse(response, content_type='application/javascript; charset=utf-8')
                else:
                    return render_to_response('messages/preview.html',
                        {'message':message, 'message_id':message_id}, context_instance=RequestContext(request))
            else:
                raise Http404

@login_required
def search(request):
    if (request.method == 'POST') and request.REQUEST['message_id']:
        return HttpResponseRedirect(reverse('message-detail', args=[request.REQUEST['message_id']]))
    return HttpResponseRedirect(reverse('main-index'))
