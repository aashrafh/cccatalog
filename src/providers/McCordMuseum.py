"""
Content Provider:       McCord Museum - Collections of artwork that celebrates Canadian History.

ETL Process:            Identify images from their art collection that are available under a
                        Creative Commons license.

Output:                 TSV file containing images of artworks and their respective meta-data.
"""
from Provider import Provider
import logging
from bs4 import BeautifulSoup
from urlparse import urlparse
import json
import re


logging.basicConfig(format='%(asctime)s - %(name)s: [%(levelname)s] =======> %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class McCordMuseum(Provider):

    def __init__(self, _name, _domain, _cc_index):
        Provider.__init__(self, _name, _domain, _cc_index)


    def getForeignID(self, _str):
        foreignID = re.search('.*?/([A-Z]{1}-?\d+(.\d{1,})?)/?$', _str)

        try:
            return foreignID.group(1)
        except:
            logger.error('Identifier not detected in: {}'.format(_str))
            return None


    def getMetaData(self, _html, _url):
        """

        Parameters
        ------------------
        _html: string
            The HTML page that was extracted from Common Crawls WARC file.

        _url: string
            The url for the webpage.


        Returns
        ------------------
        A tab separated string which contains the meta data that was extracted from the HTML.

        """

        soup                = BeautifulSoup(_html, 'html.parser')
        otherMetaData       = {}
        src                 = None
        license             = None
        version             = None
        imageURL            = None
        formatted           = None

        self.clearFields()
        self.translationAvailable   = True
        self.watermarked            = 't'

        #verify the license
        licenseInfo = soup.find('a', {'rel': 'license', 'href': True})
        if licenseInfo:
            ccURL               = urlparse(licenseInfo.attrs['href'].strip())
            license, version    = self.getLicense(ccURL.netloc, ccURL.path, _url)

            if not license:
                logger.warning('License not detected in url: {}'.format(_url))
                return None

            self.license          = license
            self.licenseVersion   = version

        #get the image and dimensions
        imgContent = soup.find('div', {'class': 'image'})
        if imgContent:
            imgSRC          = imgContent.findChild('img')
            self.url        = self.validateContent('', imgSRC, 'src')
            if self.url:
                self.url    = '{}{}'.format(self.domain, self.url)


            self.width      = self.validateContent('', imgSRC, 'width')
            self.height     = self.validateContent('', imgSRC, 'height')
            self.thumbnail  = self.url.replace('/ObjView/', '/ListView/')
            #self.url        = self.url.replace('/ObjView/', '/largeimages/') #removed because of inconsistent dimensions.


            imgAltText  = self.validateContent('', imgSRC, 'alt')
            if imgAltText:
                otherMetaData['image_alt_text'] = imgAltText


        else:
            logger.warning('Image not detected in url: {}'.format(_url))
            return None


        self.foreignLandingURL  = _url

        #get the title
        title   = soup.find('h1', {'class': 'vo'})
        if title:
            title       = title.text.split('|')
            self.title  = title[1].strip().encode('unicode-escape')
            foreignID   = title[0].strip().encode('unicode-escape')

        if foreignID:
            self.foreignIdentifier = foreignID.strip()
        else:
            logger.warning('Identifier not detected in: {}'.format(_url))
            return None


        #tags
        tagInfo = soup.find_all('a', {'title': 'All tagged images'})
        if tagInfo:
            tags                    = ','.join(tag.text.strip().encode('unicode-escape') for tag in tagInfo)
            otherMetaData['tags']   = tags


        otherInfo = soup.find('div', {'id': 'etiquette'})
        if otherInfo:
            artisrtInfo = otherInfo.findChild('a', {'href': re.compile('.*?tablename=artist.*?')})
            if artisrtInfo:
                artist       = artisrtInfo.text.strip().split(' (')[0]
                self.creator = artist.encode('unicode-escape')


        #description/summary
        description = soup.find('div', {'id': 'descriptions'})
        if description:
            content = description.text.strip().encode('unicode-escape')
            if content:
                otherMetaData['description'] = content


        self.provider   = self.name
        self.source     = 'commoncrawl'

        if otherMetaData:
            self.metaData   = otherMetaData


        formatted = list(self.formatOutput)

        return formatted