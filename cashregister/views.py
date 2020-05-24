# django library
from django.db.models import Q
from django.urls import reverse
from django.conf import settings
from django.shortcuts import render
from django.contrib import messages
from django.utils.timezone import now
from django.views.generic import View
from django.http import HttpResponse, HttpResponseRedirect

# pdfkit library
import pdfkit

# my functions
from functions.archive import check_FTPconn
from functions.myfunctions import cashregisterdata, cashregisterhtml2pdf, sendemail, cashaccept2pdf, make_attachment, previous_month_year

# my models
from cashregister.models import Company, CashRegister

# my forms
from cashregister.forms import CompanyAddForm, CashRegisterForm

# my validators
from validators.my_validator import contents_variants


# Create your views here.


class CompanyAddView(View):
	'''class implementing the method of adding/changing basic data for the new or existing company'''

	def get(self, request, company_id:int = None) -> render:
		companies = Company.objects.order_by('company')
		if company_id:
			company = Company.objects.get(pk=company_id)
			fields = list(company.__dict__.keys())[4:]
			initial = Company.objects.filter(pk=company_id).values(*fields)[0]
			form = CompanyAddForm(initial=initial)
			context = {'form': form, 'company_id': company_id, 'companies': companies}

		else:
			form = CompanyAddForm()
			context = {'form': form, 'companies': companies}

		return render(request, 'cashregister/company_add.html', context)

	def post(self, request, company_id:int = None) -> HttpResponseRedirect:
		args = [company_id]
		companies = Company.objects.all().order_by('company')
		form = CompanyAddForm(data=request.POST)
		context = {'form': form, 'companies': companies}

		if company_id:
			company = Company.objects.get(pk=company_id)
			fields = list(company.__dict__.keys())[4:]
			old_values = Company.objects.filter(pk=company_id).values(*fields)[0]
			old_values['status'] = str(old_values['status'])
		else:
			old_values = {'nip': request.POST['nip']}

		if form.is_valid():
			new_values = form.cleaned_data

			if new_values!=old_values:
				try:
					obj, created = Company.objects.update_or_create(defaults=new_values, **old_values)
					args = [obj.id]

					if created:
						msg = f'Successful created new company {obj}'
						messages.success(request, msg)
					else:
						msg = f'Successful update data for company {obj}'
						messages.success(request, msg)

				except Company.DoesNotExist:
					messages.warning(request, r'Somthing wrong... try again!')

			else:
				messages.info(request, r'Nothing to change!')

			return HttpResponseRedirect(reverse('cashregister:change_company', args=args))

		else:
			return render(request, 'cashregister/company_add.html', context)


class CashRegisterView(View):
	'''class implementing the method of adding records to the Cash Register'''

	def get(self, request, company_id:int=None) -> HttpResponse:
		check = CashRegister.objects.filter(company_id=company_id)
		tags = CashRegister.objects.order_by('contents').distinct('contents').exclude(contents='z przeniesienia').values_list('contents', flat=True)
		symbols = CashRegister.objects.order_by('symbol').distinct('symbol').values_list('symbol', flat=True)
		companies = Company.objects.filter(status__range=[1, 3]).order_by('company')
		context = {'companies': companies, 'tags': list(tags), 'symbols': list(symbols)}

		if company_id:
			month, year = now().month, now().year
			company = Company.objects.get(pk=company_id)
			registerdata = cashregisterdata(company_id, month, year)
			context.update(dict(registerdata))
			records = check.filter(created__month=month, created__year=year).exclude(contents='z przeniesienia')
			form = CashRegisterForm(initial={'company': company})
			query = Q(company_id=company_id)&(Q(created__year=year)|Q(created__year=year-1))
			cr_data = CashRegister.objects.filter(query).exclude(contents='z przeniesienia')
			cr_set = cr_data.datetimes('created','month', order='DESC')
			context.update({'form': form, 'company': company, 'company_id': company_id,
			                'cr_set': cr_set, 'records': records.order_by('-created')})

			pm, py = previous_month_year(month, year)
			previous = check.filter(created__month=pm, created__year=py)

			if previous:
				context.__setitem__('previous', True)
			else:
				context.__setitem__('previous', False)

		return render(request, 'cashregister/cashregister.html', context)

	def post(self, request, company_id:int=None) -> HttpResponseRedirect:
		form = CashRegisterForm(data=request.POST)
		check = CashRegister.objects.filter(company_id=company_id)
		companies = Company.objects.filter(status__in=[1,2,3]).order_by('company')
		context = {'form': form, 'companies': companies}

		if company_id:
			month, year = now().month, now().year
			company = Company.objects.get(pk=company_id)
			registerdata = cashregisterdata(company_id, month, year)
			context.update(dict(registerdata))
			records = check.filter(created__month=month, created__year=year).exclude(contents='z przeniesienia')
			query = Q(company_id=company_id)&(Q(created__year=year)|Q(created__year=year-1))
			cr_data = CashRegister.objects.filter(query).exclude(contents='z przeniesienia')
			cr_set = cr_data.datetimes('created','month', order='DESC')
			context.update({'company': company, 'company_id': company_id,
			                'cr_set': cr_set, 'records': records.order_by('-created')})

			pm, py = previous_month_year(month, year)
			previous = check.filter(created__month=pm, created__year=py)

			if previous:
				context.__setitem__('previous', True)
			else:
				context.__setitem__('previous', False)

			if form.is_valid():
				form.save(commit=False)
				data = form.cleaned_data
				income, expenditure = [data[key] for key in ('income', 'expenditure')]
				if income != 0 and expenditure != 0:
					msg = f'One of the fields (income {income:.2f}PLN or expenditure {expenditure:.2f}PLN) must be zero and second have to be positive value!'
					messages.warning(request, msg)
					return render(request, 'cashregister/cashregister.html', context)
				elif income or expenditure:
					if income > 0:
						form.save(commit=True)
						msg = f'Succesful register new record in {company} (income={income:.2f}PLN)'
						messages.success(request, msg)
					elif expenditure > 0:
						if registerdata['status'] - expenditure > 0:
							form.save(commit=True)
							msg = f'Succesful register new record in {company} (expenditure={expenditure:.2f}PLN)'
							messages.success(request, msg)
						else:
							msg = f"Expenditure ({expenditure:.2f}PLN) is greater than the cash register status ({registerdata['status']:.2f}PLN)!"
							messages.warning(request, msg)
			else:
				contents = request.POST['contents']
				if contents in contents_variants:
					msg = f'<<{contents}>> is not allowed! Use any other...'
					messages.info(request, msg)

		return HttpResponseRedirect(reverse('cashregister:cash_register', args=[company_id]))


class CashRegisterDelete(View):
	'''class enabling deleting records in the cash report'''

	def get(self, request, company_id:int, record:int) -> HttpResponseRedirect:
		record = CashRegister.objects.get(pk=record)
		if record:
			record.delete()
			msg = f'Succesful erase record <<{record.symbol}, {record.contents} in Cash register for {record.company}'
			messages.info(request, msg)
		return HttpResponseRedirect(reverse('cashregister:cash_register', args=[company_id]))


class CashRegisterPrintView(View):
	'''class representing the view of monthly cash register print'''
	def get(self, request, company_id:int):
		'''convert html cashregister_pdf for selected company to pdf'''
		month, year = now().month, now().year
		month, year = previous_month_year(month, year)

		html = cashregisterhtml2pdf(company_id, month, year)

		if html:
			# create cash register as pdf file attachment
			filename = f'cashregister_{company_id}_{year}_{month}.pdf'
			response = make_attachment(html, filename)

			return response
		else:
			messages.warning(request, r'Nothing to print...')

		return HttpResponseRedirect(reverse('cashregister:cash_register', args=[company_id]))

	def post(self, request, company_id:int):
		'''convert html cashregister_pdf for selected cash register to pdf'''
		data = request.POST['cr_number']
		month, year = int(data.split('/')[0]), int(data.split('/')[1])

		html = cashregisterhtml2pdf(company_id, month, year)

		if html:
			# create cash register as pdf file attachment
			filename = f'cashregister_{company_id}_{year}_{month}.pdf'
			response = make_attachment(html, filename)

			return response
		else:
			messages.warning(request, r'Nothing to print...')

		return HttpResponseRedirect(reverse('cashregister:cash_register', args=[company_id]))


class CashRegisterSendView(View):
	'''class representing the view for sending cash register as pdf file'''

	def get(self, request, company_id:int) -> HttpResponseRedirect:

		if check_FTPconn():
			company = Company.objects.get(pk=company_id)

			month, year = now().month, now().year
			month, year = previous_month_year(month, year)

			html = cashregisterhtml2pdf(company_id, month, year)

			if html:
				# create pdf file and save on templates/pdf/cashregister_{company}_{month}_{year}.pdf
				options = {'page-size': 'A4', 'margin-top': '0.4in', 'margin-right': '0.2in', 'margin-bottom': '0.4in',
				           'margin-left': '0.6in', 'encoding': "UTF-8", 'orientation': 'portrait', 'no-outline': None,
				           'quiet': ''}
				pdfile = f'templates/pdf/cashregister_{company}_{month}_{year}.pdf'
				pdfkit.from_string(html, pdfile, options=options, css=settings.CSS_FILE)
				# send e-mail with attached cash register as file in pdf format
				mail = {'subject': f'cash register for {month}/{year} r.',
				        'message': f'Cash Register for {company} on {month}/{year} in attachment ...',
				        'sender': settings.EMAIL_HOST_USER, 'recipient': ['projekt@unikolor.com'], 'attachments': [pdfile]}
				sendemail(**mail)
				messages.info(request, f'Cash register for {company} on {month}/{year} was sending....')
			else:
				messages.warning(request, r'Nothing to send...')
		else:
			messages.error(request, 'Occurred problem with internet connection...')

		return HttpResponseRedirect(reverse('cashregister:cash_register', args=[company_id]))


class CashRegisterAcceptView(View):
	'''class enabling printing cash accept from the cash report'''

	def get(self, request, company_id:int, record:int) -> HttpResponse:
		html = cashaccept2pdf(record)
		if html:
			# create pdf file and save on templates/pdf/cashaccept_{record}.pdf
			filename = f'cashaccept_{record}.pdf'
			response = make_attachment(html, filename)
			return response
		else:
			messages.warning(request, r'Nothing to print...')

		return HttpResponseRedirect(reverse('cashregister:cash_register', args=[company_id]))
