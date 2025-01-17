import pytest
from mixer.backend.django import mixer
from apps.reports.models import ParticipantsReport
from django.db import IntegrityError
from apps.core.models import Message, Room
from apps.reports.tasks import (create_participants_object,
                                get_participants_daily,
                                get_participants_monthly,
                                get_participants_yearly,
                                get_participants_all_the_time)
from datetime import date, datetime, timedelta
from django.urls import reverse
import json
from rest_framework.test import APIClient
import calendar


class TestParticipantsReport():
    @pytest.mark.django_db
    def test_participants_create(self):
        participants = mixer.blend(ParticipantsReport)
        assert ParticipantsReport.objects.count() == 1
        assert participants.__str__() == ('{} - {}').format(
            participants.start_date.strftime("%d/%m/%Y"), participants.period)

    @pytest.mark.django_db
    def test_participants_integrity_error(self):
        content = mixer.blend(ParticipantsReport)
        with pytest.raises(IntegrityError) as excinfo:
            mixer.blend(ParticipantsReport,
                        period=content.period,
                        start_date=content.start_date)
        assert 'UNIQUE constraint failed' in str(
            excinfo.value)
        ## PostgreSQL message error
        # assert 'duplicate key value violates unique constraint' in str(
        #     excinfo.value)

    @pytest.mark.django_db
    def test_create_participants_daily(self):
        data_daily = ['2020-11-23', 10]
        participants_object = create_participants_object(data_daily, 'daily')

        assert participants_object.period == 'daily'
        assert participants_object.start_date == '2020-11-23'
        assert participants_object.end_date == '2020-11-23'
        assert participants_object.participants == 10

    @pytest.mark.django_db
    def test_create_participants_monthly(self):
        data_monthly = ['2020-11', 10]

        participants_object = create_participants_object(data_monthly, 'monthly')

        assert participants_object.period == 'monthly'
        assert participants_object.start_date == date(2020, 11, 1)
        assert participants_object.end_date == date(2020, 11, 30)
        assert participants_object.participants == 10

    @pytest.mark.django_db
    def test_create_participants_yearly(self):
        data_yearly = ['2019', 10]

        participants_object = create_participants_object(data_yearly, 'yearly')

        assert participants_object.period == 'yearly'
        assert participants_object.start_date == date(2019, 1, 1)
        assert participants_object.end_date == date(2019, 12, 31)
        assert participants_object.participants == 10

    @pytest.mark.django_db
    def test_get_participants_daily_without_args(self):
        yesterday = datetime.now() - timedelta(days=1)

        message = mixer.blend(Message)
        message.created = yesterday
        message.save()

        get_participants_daily.apply()

        daily_data = ParticipantsReport.objects.filter(
            period='daily').first()

        assert daily_data.start_date == yesterday.date()
        assert daily_data.end_date == yesterday.date()
        assert daily_data.period == 'daily'
        assert daily_data.participants == 1

    @pytest.mark.django_db
    def test_get_participants_monthly_without_args(self):
        yesterday = date.today() - timedelta(days=1)
        message = mixer.blend(Message)
        message.created = yesterday
        message.save()

        get_participants_monthly.apply()

        monthly_data = ParticipantsReport.objects.filter(
            period='monthly').first()

        assert monthly_data.start_date == yesterday.replace(day=1)
        assert monthly_data.end_date == yesterday
        assert monthly_data.period == 'monthly'
        assert monthly_data.participants == 1

    @pytest.mark.django_db
    def test_get_participants_yearly_without_args(self):
        yesterday = date.today() - timedelta(days=1)
        message = mixer.blend(Message)
        message.created = yesterday
        message.save()

        get_participants_yearly.apply()

        yearly_data = ParticipantsReport.objects.filter(
            period='yearly').first()

        assert yearly_data.start_date == yesterday.replace(day=1, month=1)
        assert yearly_data.end_date == yesterday
        assert yearly_data.period == 'yearly'
        assert yearly_data.participants == 1

    @pytest.mark.django_db
    def test_get_participants_yearly_current_year(self):
        yesterday = date.today() - timedelta(days=1)
        message = mixer.blend(Message)
        message.created = yesterday
        message.save()

        mixer.blend(ParticipantsReport, period='yearly', participants=0,
                    start_date=yesterday.replace(day=1, month=1),
                    end_date=yesterday - timedelta(days=1))

        get_participants_yearly.apply()

        yearly_data = ParticipantsReport.objects.filter(period='yearly').first()

        assert yearly_data.start_date == yesterday.replace(day=1, month=1)
        assert yearly_data.end_date == yesterday
        assert yearly_data.period == 'yearly'
        assert yearly_data.participants == 1

    @pytest.mark.django_db
    def test_get_participants_all_the_time(self):
        yesterday = date.today() - timedelta(days=1)
        initial_date = date(year=2020, month=1, day=1)

        first_room = mixer.blend(Room)
        first_room.created = initial_date
        first_room.save()

        mixer.blend(ParticipantsReport, period='all', participants=0,
                    start_date=initial_date,
                    end_date=yesterday - timedelta(days=1))

        message = mixer.blend(Message)
        message.created = yesterday
        message.save()

        get_participants_all_the_time.apply()

        all_data = ParticipantsReport.objects.get(period='all')

        assert all_data.start_date == initial_date
        assert all_data.end_date == yesterday
        assert all_data.period == 'all'
        assert all_data.participants == 1

    @pytest.mark.django_db
    def test_participants_api_url(api_client):
        mixer.cycle(5).blend(ParticipantsReport)
        url = reverse('participantsreport-list')
        client = APIClient()
        response = client.get(url)
        request = json.loads(response.content)

        assert response.status_code == 200
        assert request['count'] == 5
