import logging
import os
import pytest
import requests
import json
from operator import itemgetter
from unittest.mock import patch, MagicMock

import thingiverse as tiv

RESOURCES = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'tests/resources/thingiverse'
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s:  %(message)s',
    level=logging.DEBUG,
)


def _get_resource_json(json_name):
    with open(os.path.join(RESOURCES, json_name)) as f:
        resource_json = json.load(f)
    return resource_json


def test_derive_timestamp_pair():
    # Note that the timestamps are derived as if input was in UTC.
    start_ts = tiv._derive_timestamp_pair('2020-03-02')
    assert start_ts == '1515974400'


def test_get_response_json_retries_with_none_response():
    with patch.object(
            tiv.delayed_requester,
            'get',
            return_value=None
    ) as mock_get:
        with pytest.raises(Exception):
            assert tiv._get_response_json_list({}, retries=2)

    assert mock_get.call_count == 3


def test_get_response_json_retries_with_non_ok():
    r = requests.Response()
    r.status_code = 504
    r.json = MagicMock(return_value={'batchcomplete': ''})
    with patch.object(
            tiv.delayed_requester,
            'get',
            return_value=r
    ) as mock_get:
        with pytest.raises(Exception):
            assert tiv._get_response_json_list({}, retries=2)

    assert mock_get.call_count == 3


def test_get_response_json_retries_with_error_json():
    r = requests.Response()
    r.status_code = 200
    r.json = MagicMock(return_value={'error': ''})
    with patch.object(
            tiv.delayed_requester,
            'get',
            return_value=r
    ) as mock_get:
        with pytest.raises(Exception):
            assert tiv._get_response_json_list({}, retries=2)

    assert mock_get.call_count == 3


def test_get_response_json_returns_response_json_when_all_ok():
    expect_response_json = {'batchcomplete': ''}
    r = requests.Response()
    r.status_code = 200
    r.json = MagicMock(return_value=expect_response_json)
    with patch.object(
            tiv.delayed_requester,
            'get',
            return_value=r
    ) as mock_get:
        actual_response_json = tiv._get_response_json_list({}, retries=2)

    assert mock_get.call_count == 1
    assert actual_response_json == expect_response_json


def test_build_query_params_default():
    actual_query_params = tiv._build_query_params()
    expect_query_params = {
        'access_token': '',
        'per_page': 30,
        'page': 1
    }

    assert actual_query_params == expect_query_params


def test_build_query_params_with_givens():
    actual_query_params = tiv._build_query_params(page=3)
    expect_query_params = {
        'access_token': '',
        'per_page': 30,
        'page': 3
    }

    assert actual_query_params == expect_query_params


def test_build_thing_query_with_givens():
    actual_endpoint, actual_query_params = tiv._build_thing_query(5)
    expect_query_params = {
        'access_token': '',
    }
    expected_endpoint = 'https://api.thingiverse.com/things/5'

    assert actual_query_params == expect_query_params and actual_endpoint == expected_endpoint


def test_validate_license_with_all_ok():
    response_json = _get_resource_json('example_thing_data.json')
    actual_license, actual_license_version = tiv._validate_license(
        response_json)
    expected_license = 'CC0'
    expected_license_version = '1.0'

    assert actual_license == expected_license
    assert actual_license_version == expected_license_version


def test_validate_license_with_license_not_detected():
    actual_license, actual_license_version = tiv._validate_license({})
    expected_license = None
    expected_license_version = None

    assert actual_license == expected_license
    assert actual_license_version == expected_license_version


def test_create_meta_dict_with_keys_exist():
    response_json = _get_resource_json('example_thing_data.json')
    actual_meta_data = tiv._create_meta_dict(response_json)
    expected_meta_data = {
        'description': "It's a double-ended hook. Rather like a shower curtain hook.\r\n",
        'title': "MakerBot Hook"
    }

    assert actual_meta_data == expected_meta_data


def test_create_meta_dict_with_keys_not_exist():
    actual_meta_data = tiv._create_meta_dict({})
    expected_meta_data = {
        'description': '',
        'title': ''
    }

    assert actual_meta_data == expected_meta_data


def test_get_things_batch_all_ok():
    expected_thing_batch = _get_resource_json('example_thing_batch.json')
    actual_thing_batch = tiv._get_things_batch(3)
    assert actual_thing_batch == expected_thing_batch


def test_get_things_batch_none_response():
    actual_thing_batch = tiv._get_things_batch(999999)
    assert len(actual_thing_batch) == 0


def test_build_foreign_landing_url():
    response_json = _get_resource_json('example_thing_data.json')
    actual_url = tiv._build_foreign_landing_url(
        response_json,
        5
    )
    expect_url = "https://www.thingiverse.com/thing:5"
    assert actual_url == expect_url


def test_build_foreign_landing_url_nones_with_empty_data():
    actual_url = tiv._build_foreign_landing_url(
        {},
        5
    )
    expect_url = "https://www.thingiverse.com/thing:5"
    assert actual_url == expect_url


def test_build_creator_data():
    response_json = _get_resource_json('example_thing_data_for_creator.json')
    actual_creator, actual_creator_url = tiv._build_creator_data(response_json)
    expected_creator = "Matt Moses"
    expected_creator_url = "https://www.thingiverse.com/mattmoses"

    assert actual_creator == expected_creator
    assert actual_creator_url == expected_creator_url


def test_build_creator_data_no_creator_name():
    response_json = _get_resource_json('example_thing_data.json')
    actual_creator, actual_creator_url = tiv._build_creator_data(response_json)
    expected_creator = "replicator"
    expected_creator_url = "https://www.thingiverse.com/replicator"

    assert actual_creator == expected_creator
    assert actual_creator_url == expected_creator_url


def test_build_creator_data_no_creator():
    actual_creator, actual_creator_url = tiv._build_creator_data({})
    expected_creator = None
    expected_creator_url = None

    print(actual_creator)
    assert actual_creator == expected_creator
    assert actual_creator_url == expected_creator_url


def test_build_creator_data_no_public_url():
    response_json = _get_resource_json('example_thing_data_for_creator.json')
    del response_json['creator']['public_url']
    actual_creator, actual_creator_url = tiv._build_creator_data(response_json)
    expected_creator = "Matt Moses"
    expected_creator_url = None

    assert actual_creator == expected_creator and actual_creator_url == expected_creator_url


def test_create_tags_list_makes_tags_list():
    expected_tags_list = _get_resource_json('example_thing_920_tags.json')
    expected_tags_list = list(map(lambda tag: {'name': str(
        tag['name'].strip()), 'provider': 'thingiverse'}, expected_tags_list))
    expected_tags_list.sort(key=itemgetter('name'))
    actual_tags_list = tiv._create_tags_list(
        str(920), 'https://api.thingiverse.com/things/920')

    assert len(actual_tags_list) == len(expected_tags_list)
    assert all(
        [element in actual_tags_list for element in expected_tags_list]
    )


def test_get_image_list_json_with_ok_response():
    actual_image_list = tiv._get_image_list_json(
        str(920), 'https://api.thingiverse.com/things/920')
    expected_image_list = _get_resource_json(
        'example_thing_920_image_list.json')

    print(actual_image_list)
    assert len(actual_image_list) == len(expected_image_list)
    assert all(
        [element in actual_image_list for element in expected_image_list]
    )


def test_get_image_meta_data():
    image_list = _get_resource_json('example_thing_920_image_list.json')
    description = _get_resource_json('thing_920_description.json')
    for image in image_list:
        actual_meta_data = tiv._get_image_meta_data(
            image, description['description'])
        expected_meta_data = {
            'description': description['description'],
            '3d_model': "https://thingiverse-beta-new.s3.amazonaws.com/assets/b6/12/ec/6e/a0/syringePump_parts.dxf"
        }

        print(actual_meta_data)
        assert actual_meta_data == expected_meta_data


def test_get_image_list():
    thing_meta_data = _get_resource_json('thing_920_description.json')
    meta_data = {
        "description": thing_meta_data["description"],
        "title": thing_meta_data["title"]
    }

    actual_total_images = tiv._get_image_list(920, 'https://api.thingiverse.com/things/920', meta_data, "https://www.thingiverse.com/thing:920", 'CC0',
                                              '1.0', "Matt Moses", "https://api.thingiverse.com/users/mattmoses", list(map(lambda tag: {'name': str(tag['name'].strip()), 'provider': 'thingiverse'}, _get_resource_json("example_thing_920_tags.json"))).sort(key=itemgetter('name')))

    assert actual_total_images == 9


def test_process_thing():
    actual_total_images = tiv._process_thing(920, '1515974400', '1516060800')

    assert actual_total_images == 9


def test_get_response_json_list_batch_endpoint():
    endpoint = 'https://api.thingiverse.com/newest'
    query_params = {
        'access_token': '',
        'per_page': 30,
        'page': 55
    }
    response_json = tiv._get_response_json_list(query_params, endpoint, 5)

    assert response_json == _get_resource_json('test_batch_endpoint.json')


def test_get_response_json_list_tags_endpoint():
    endpoint = 'https://api.thingiverse.com/things/4198944/tags'
    query_params = {
        'access_token': ''
    }
    response_json = tiv._get_response_json_list(query_params, endpoint, 5)
    with open('test_tags_endpoint.json', 'w') as outfile:
        json.dump(response_json, outfile)

    assert response_json == _get_resource_json('test_tags_endpoint.json')


def test_process_image_list():
    expected_list = [[
        '39074',
        'https://thingiverse-rerender-new.s3.amazonaws.com/renders/44/12/6a/5a/bf/makerbot_chin_rest_display_large.jpg',
        'https://thingiverse-rerender-new.s3.amazonaws.com/renders/44/12/6a/5a/bf/makerbot_chin_rest_display_medium.jpg',
        json.dumps({
            'description': "I didn't want the makerbotters to feel left out.  I watch mine more than I read anymore.  Derived from http://www.thingiverse.com/thing:5410 and http://www.thingiverse.com/thing:4537",
            '3d_model': 'https://cdn.thingiverse.com/assets/c1/98/eb/67/fd/makerbot_chin_rest.stl'
        })
    ]]
    print(expected_list)
    json_file = _get_resource_json('test_process_image_list.json')
    actual_list = tiv._process_image_list(
        json_file, "I didn't want the makerbotters to feel left out.  I watch mine more than I read anymore.  Derived from http://www.thingiverse.com/thing:5410 and http://www.thingiverse.com/thing:4537")
    print(actual_list)

    assert len(expected_list) == len(actual_list)
    assert all(
        [element in actual_list for element in expected_list]
    )
