# Searches commonly used general repositories for datasets/software associated with a specific institution. 
# Identifiers can be changed in main().
# There is no guarantee of uniqueness of each individual dataset, as some datasets may be hosted on multiple repositories.
# Results can be consolidated in Excel to remove duplicates.
# Author: Kevin Leonard
# Date: February 16, 2023

from sickle import Sickle
from pangaeapy import PanQuery
import swagger_client
from swagger_client.rest import ApiException
import csv
import requests
import json
from ratelimit import limits, RateLimitException, sleep_and_retry
from bs4 import BeautifulSoup
from requests.structures import CaseInsensitiveDict


# The DataCite search operates using the ROR of the institution
def datacite(ror, fileIdentifier): 
    print("Beginning DataCite extraction:")
    ror = ror[16:]
    currentPage = 'https://api.datacite.org/dois?query=creators.affiliation.affiliationIdentifier:*' + ror + '* AND types.resourceTypeGeneral:Dataset'

    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/x-dc+xml"

    response = requests.get(currentPage,
                            headers=headers)
    response.json()
    pythonObj = json.loads(response.text)

    doiList = []
    numRecords = 0

    # Iterate through all pages
    while(currentPage):
        response = requests.get(currentPage,
            headers=headers)
        response.json()
        pythonObj = json.loads(response.text)
        
        num = 0
        for x in pythonObj['data']:
            record = []
            record.append(pythonObj['data'][num]['id'])
            record.append(pythonObj['data'][num]['attributes']['creators'])
            record.append(pythonObj['data'][num]['attributes']['descriptions'])
            record.append(pythonObj['data'][num]['attributes']['publicationYear'])
            record.append(pythonObj['data'][num]['attributes']['titles'])
            doiList.append(record)
            num += 1
            numRecords += 1
            print(f"\rDataCite datasets extracted: {numRecords}", end='', flush=True)

        try:
            currentPage = pythonObj['links']['next']
        except KeyError:
            break

    #Write list of DOIs to csv
    fileName = fileIdentifier + '_Datacite_Datasets.csv'
    with open(fileName, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["DOI", "Creators", "Description", "Year", "Title"])
            for record in doiList:
                writer.writerow(record)
    print("\nDataCite extraction complete.\n")


# Zenodo search uses various institutional search terms. Datasets and software are identified separately.
def zenodo(searchTerms, fileIdentifier, ACCESS_TOKEN):
    print("Beginning Zenodo dataset extraction.")
    ONE_MINUTE = 60

    # Rate limit, as Zenodo limits calls to 60 per minute
    @sleep_and_retry
    @limits(calls=60, period=ONE_MINUTE)
    def call_api(oaiID):
        record = sickle.GetRecord(identifier=oaiID, metadataPrefix='oai_dc')

        if response.status_code != 200:
            raise Exception('API response: {}'.format(response.status_code))
        return record

    sickle = Sickle('https://zenodo.org/oai2d')
    
    doiList = []
    oaiIDs = [] #contains the OAI identifiers necessary for use with Sickle OAI-PMH
    numRecords = 0

    # Generate search query  based on provided search terms 
    searchQuery = 'creators.affiliation:("'
    temp = len(searchTerms) - 1
    for x in range(len(searchTerms) - 1):
        searchQuery = searchQuery + searchTerms[x] + '" OR "'
    searchQuery = searchQuery + searchTerms[temp] + '")'

    sickle = Sickle('https://zenodo.org/oai2d')
    currentPage = 'https://zenodo.org/api/records'

    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/x-dc+xml"

    # Iterate through all pages for datasets
    while(currentPage):
        response = requests.get(currentPage,
        headers=headers,
                            params={'q': searchQuery,
                            'type': 'dataset', # The 'type' value can be set as: Publication, Dataset, Image, Software, Presentation, Poster, Video, Lesson, Other
                            'access_token': ACCESS_TOKEN})
        pythonObj = json.loads(response.text)
        num = 0
        for x in pythonObj['hits']['hits']:
            doiList.append(pythonObj['hits']['hits'][num]['doi'])
            oaiIDs.append(pythonObj['hits']['hits'][num]['id'])
            num += 1
            numRecords += 1
            print(f"\rZenodo dataset records extracted: {numRecords}", end='', flush=True)
        try:
            currentPage = pythonObj['links']['next']
        except KeyError:
            break
    print("\nZenodo dataset extraction complete.\n")

    numRecords = 0

    # Repeat process for software
    print("Beginning Zenodo software extraction.")
    currentPage = 'https://zenodo.org/api/records'
    while(currentPage):
        response = requests.get(currentPage,
        headers=headers,
                            params={'q': searchQuery,
                            'type': 'software', # The 'type' value can be set as: Publication, Dataset, Image, Software, Presentation, Poster, Video, Lesson, Other
                            'access_token': ACCESS_TOKEN})
        response.json()
        pythonObj = json.loads(response.text)
        num = 0
        for x in pythonObj['hits']['hits']:
            doiList.append(pythonObj['hits']['hits'][num]['doi'])
            oaiIDs.append(pythonObj['hits']['hits'][num]['id'])
            num += 1
            numRecords += 1
            print(f"\rZenodo software records extracted: {numRecords}", end='', flush=True)
        try:
            currentPage = pythonObj['links']['next']
        except KeyError:
            break
    print("\nZenodo software extraction complete.\n")

    #Use Sickle to write a subset of the metadata of each record to CSV
    fileName = fileIdentifier + '_Zenodo_Datasets_Software.csv'
    with open(fileName, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["DOI"])
            # for oai in oaiIDs:
            for doi in doiList:
                # NOTE: The below codeblock can be put in place to extract more detailed metadata from Zenodo, but it significantly increases the runtime of the code due to repeated API calls.

                # oaiID = 'oai:zenodo.org:' + str(oai)
                # record = call_api(oaiID)
                # doi = record.metadata.get('identifier')[0][16:]
                # # url = record.metadata.get('identifier')[0]
                # # zenodoIdentifier = record.metadata.get('identifier')[2]
                # date = record.metadata.get('date')[0]
                # creator = record.metadata.get('creator')
                # title = record.metadata.get('title')[0]
                # fileType = record.metadata.get('type')[1]
                # keyWords = record.metadata.get('subject')
                # relatedItems = record.metadata.get('relation')
                # writer.writerow([doi,url,zenodoIdentifier,date,creator,title,fileType, keyWords])

                writer.writerow([doi])


# Dryad searches uses the ROR ID to search for datasets
def dryad(ror, fileIdentifier):
    print("Beginning Dryad extraction:")
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"

    doiList = []

    num = 0
    numRecords = 0

    currentPage = 'https://datadryad.org/api/v2/search?q=' + ror

    # Iterate through all Dryad pages
    while(currentPage):
        response = requests.get(currentPage,
                            headers=headers,
                            params={'affiliation': ror})
        response.json()
        pythonObj = json.loads(response.text)
        num = 0

        for x in pythonObj['_embedded']['stash:datasets']:
            record = []
            record.append(pythonObj['_embedded']['stash:datasets'][num]['identifier'])
            try:
                record.append(pythonObj['_embedded']['stash:datasets'][num]['publicationDate'])
                record.append(pythonObj['_embedded']['stash:datasets'][num]['title'])
                record.append(pythonObj['_embedded']['stash:datasets'][num]['authors'])
            except KeyError:
                break
            doiList.append(record)
            num += 1
            numRecords += 1
            print(f"\rDryad dataset records extracted: {numRecords}", end='', flush=True)
        try:
            currentPage = "https://datadryad.org" + str(pythonObj['_links']['next']['href'])
        except KeyError:
            break


    #Write list of DOIs to csv
    fileName = fileIdentifier + '_Dryad_Datasets.csv'
    with open(fileName, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["DOI", "Date", "Title", "Creators"])
            for record in doiList:
                doi = record[0][4:]
                publicationDate = record[1]
                title = record[2]
                authors = record[3]
                writer.writerow([doi, publicationDate, title, authors])
    print("\nDryad dataset extraction complete.\n")


# OSF search requires that the institution has an OSF ID. The code then extracts the details of all records associated with that institution ID.
def osf(osfID, fileIdentifier, ACCESS_TOKEN):
    print("Beginning OSF extraction:")
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/x-dc+xml"

    osfIdList = []
    doiList = []
    numRecords = 0

    currentPage = 'https://api.osf.io/v2/institutions/' + osfID + '/nodes/'

    # Iterate through all pages of OSF results
    while(currentPage):
        response = requests.get(currentPage,
        headers=headers,
                            params={
                            'access_token': ACCESS_TOKEN})
        response.json()
        pythonObj = json.loads(response.text)

        num = 0

        for x in pythonObj['data']:
            osfIdList.append(pythonObj['data'][num]['id'])
            identifiersHTML = pythonObj['data'][num]['relationships']['identifiers']['links']['related']['href']
            
            # Complete second GET request on the link containing identifiers
            response2 = requests.get(identifiersHTML,
                headers=headers,
                params={'access_token': ACCESS_TOKEN}
                )
            
            response2.json()
            identifierJSON = json.loads(response2.text)
            try:
                if identifierJSON['data'][0]['attributes']['category'] == 'ark': # Avoid using ARK identifier, extract DOI instead
                    doiList.append(identifierJSON['data'][1]['attributes']['value'])
                else:
                    doiList.append(identifierJSON['data'][0]['attributes']['value'])
            except IndexError:
                doiList.append("No DOI")
            num +=1
            numRecords += 1
            print(f"\rOSF dataset records extracted: {numRecords}", end='', flush=True)

        try:
            currentPage = pythonObj['links']['next']
        except KeyError:
            break
    print("\nOSF project extraction complete.\n")

    # Write results to CSV
    fileName = fileIdentifier + '_OSF_Datasets.csv'
    with open(fileName, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["OSF Node ID", "DOI"])
            num = 0
            for x in doiList:
                writer.writerow([osfIdList[num], doiList[num]])
                num +=1


# Pangaea search uses various institutional search terms.
def pangaea(pangaeaSearchTerms, fileIdentifier):
    print("Beginning Pangaea extraction:")
    doiList = []
    numRecords = 0

    searchQuery = ''
    temp = len(pangaeaSearchTerms) - 1
    for x in range(len(pangaeaSearchTerms) - 1):
        searchQuery = searchQuery + pangaeaSearchTerms[x] + ' OR '
    searchQuery = searchQuery + pangaeaSearchTerms[temp]

    query = PanQuery._search(PanQuery, searchQuery, limit=1000)

    index = 0
    for x in query:
        doiList.append(query[index]['URI'])
        index += 1
        numRecords += 1
        print(f"\rPangaea dataset records extracted: {numRecords}", end='', flush=True)

    query = PanQuery._search(PanQuery, searchQuery, limit=1000, offset=500)
    index = 0
    for x in query:
        doiList.append(query[index]['URI'])
        index += 1
        numRecords += 1
        print(f"\rPangaea dataset records extracted: {numRecords}", end='', flush=True)

    query = PanQuery._search(PanQuery, searchQuery, limit=1000, offset=1000)
    index = 0
    for x in query:
        doiList.append(query[index]['URI'])
        index += 1
        numRecords += 1
        print(f"\rPangaea dataset records extracted: {numRecords}", end='', flush=True)

    query = PanQuery._search(PanQuery, searchQuery, limit=1000, offset=1500)
    index = 0
    for x in query:
        doiList.append(query[index]['URI'])
        index += 1
        numRecords += 1
        print(f"\rPangaea dataset records extracted: {numRecords}", end='', flush=True)

    fileName = fileIdentifier + '_Pangaea_Datasets.csv'
    with open(fileName, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["DOI"])
                for doi in doiList:
                    doi = doi[4:]
                    writer.writerow([doi])
    print("\nPangaea dataset extraction complete.\n")


# Figshare search uses various institutional search terms.
def figshare(figshareSearchTerms, fileIdentifier):
    # create an instance of the API class
    api_instance = swagger_client.ArticlesApi()

    print("Beginning Figshare extraction:")

    offset = 0
    limit = 1000
    
    searchQuery = ""
    temp = len(figshareSearchTerms) - 1
    for x in range(len(figshareSearchTerms) - 1):
        searchQuery = searchQuery + ":search_term: " + figshareSearchTerms[x] + " OR "
    searchQuery = searchQuery + ":search_term: " + figshareSearchTerms[temp]

    search = {"search_for": searchQuery, "offset": offset, "limit": limit, "item_type": 3} # ArticleSearch | Search Parameters (optional)
    numRecords = 0

    doiList = []
    names = []
    titles = []
    dates = []
    try: 
        # Public Articles Search
        api_response = api_instance.articles_search(search=search)
        num = 0
        for x in api_response:
            if api_response[num].doi:
                record = []
                record.append(api_response[num].doi)
                record.append(api_response[num].title)
                record.append(api_response[num].timeline.first_online[:10])
                doiList.append(record)
            else:
                # doiList.append("no DOI: " + api_response[num].url)
                record = []
                record.append(api_response[num].url)
                record.append(api_response[num].title)
                record.append(api_response[num].timeline.first_online[:10])
                doiList.append(record)
            num += 1
            numRecords += 1
            print(f"\rFigshare dataset records extracted: {numRecords}", end='', flush=True)
    except ApiException as e:
        print("Exception when calling ArticlesApi->articlesSearch: %s\n" % e)

    if num == 1000:
        offset = 1000
        search = {"search_for": searchQuery, "offset": offset, "limit": limit, "item_type": 3} # ArticleSearch | Search Parameters (optional)
        try: 
            # Public Articles Search
            api_response = api_instance.articles_search(search=search)
            num = 0
            for x in api_response:
                if api_response[num].doi:
                    record = []
                    record.append(api_response[num].doi)
                    record.append(api_response[num].title)
                    record.append(api_response[num].timeline.first_online[:10])
                    doiList.append(record)

                else:
                    # doiList.append("no DOI: " + api_response[num].url)
                    record = []
                    record.append(api_response[num].url)
                    record.append(api_response[num].title)
                    record.append(api_response[num].timeline.first_online[:10])
                    doiList.append(record)
                num += 1
                numRecords += 1
                print(f"\rFigshare dataset records extracted: {numRecords}", end='', flush=True)
        except ApiException as e:
            print("Exception when calling ArticlesApi->articlesSearch: %s\n" % e)

    fileName = fileIdentifier + '_Figshare_Datasets.csv'
    with open(fileName, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["DOI", "Title", "Date"])
            for record in doiList:
                writer.writerow([record[0], record[1], record[2]])
    print("\nFigshare dataset extraction complete.\n")


# GBIF search uses various institutional search terms.
def GBIF(GBIF_OrgID, fileIdentifier):
    print("Beginning GBIF extraction:")
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json,limit/100"

    doiList = []
    num = 0
    pagination = 0
    numRecords = 0

    currentPage = 'https://api.gbif.org/v1/dataset/search?publishing_org=' + GBIF_OrgID[0] + "&limit=500"

    response = requests.get(currentPage, headers=headers)
    response.json()
    pythonObj = json.loads(response.text)
    for x in pythonObj['results']:
        doiList.append(pythonObj['results'][num]['doi'])
        num += 1
        numRecords += 1
        print(f"\rGBIF dataset records extracted: {numRecords}", end='', flush=True)
    num = 0
    pagination += 20


    # #Write list of DOIs to csv
    fileName = fileIdentifier + '_GBIF_Datasets.csv'
    with open(fileName, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["DOI"])
            for doi in doiList:
                writer.writerow([doi])
    print("\nGBIF dataset extraction complete.\n")


def main():

    ror = "https://ror.org/00cv9y106"
    osfID = "ugent"
    osf_ACCESS_TOKEN = '' 
    zenodoSearchTerms = ['Ghent', 'UGent', 'Ghent University']
    zenodo_ACCESS_TOKEN = ''
    pangaeaSearchTerms = ['gent', 'ugent', 'ghent']
    figshareSearchTerms = ['ugent', 'ghent']
    GBIF_OrgID = ['2089ce96-4fb5-4a20-999c-3ccf45a27a4d']
    fileIdentifier = "UGent" # ID that is appended to the beginning of each output file


    if ror:
        datacite(ror, fileIdentifier)
        dryad(ror, fileIdentifier)
    if zenodoSearchTerms and zenodo_ACCESS_TOKEN:
        zenodo(zenodoSearchTerms, fileIdentifier, zenodo_ACCESS_TOKEN)
    if osfID and osf_ACCESS_TOKEN:
        osf(osfID, fileIdentifier, osf_ACCESS_TOKEN) 
    if pangaeaSearchTerms[0]:
        pangaea(pangaeaSearchTerms, fileIdentifier)
    if figshareSearchTerms[0]:
        figshare(figshareSearchTerms, fileIdentifier)
    if GBIF_OrgID[0]:
        GBIF(GBIF_OrgID, fileIdentifier)

if __name__ == "__main__":
    main()