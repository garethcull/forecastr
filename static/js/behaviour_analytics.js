
$(document).ready(function(){


    // On click of the primary cta on the landing page, send event to the data layer
    $('a[data-element="primary"]').on('click', function(e) {
       
        
        e.preventDefault();
        window.dataLayer.push({'event':'product-page-primary-cta'});
        
        // Set a 1 second delay to before navigating to the /app/ page - so that the dataLayer value is successfully set.
        setTimeout(function(){            
            
                window.location.href = '/app/'

        }, 1000);
   
    });
    
    
    // On click of the feature nav ctas on the landing page, send event to the data layer
    $('a[data-toggle="tab"]').on('click', function(e) {
       
        var txt = $(e.target).text();
        console.log(txt);
        
        window.dataLayer.push({'event':'product-page-feature-nav',
                               'linkText': txt
                              });      
    });
    
    
    // On click of outbound ctas to try forecastr, send event to the data layer
    
    
    $('a[data-element="outbound-cta"]').on('click', function(e) {
       
        
        e.preventDefault();
        var txt = this.getAttribute("data-val");
        console.log(txt);
        var href = this.getAttribute("href");
        
        
        window.dataLayer.push({'event':'product-page-outbound-link',
                               'linkText': txt
                              });  
        
        
        setTimeout(function(){            
            
                window.location.href = href;

        }, 1000);
        
        
    });
    
    
    // Internal Link clicks
    $('a[data-element="internal-link"]').on('click', function(e) {
       
        
        e.preventDefault();
        var txt = this.getAttribute("data-val");
        console.log(txt);
        var href = this.getAttribute("href");
        
        
        window.dataLayer.push({'event':'product-page-internal-link',
                               'linkText': txt
                              });  
        
        
        setTimeout(function(){            
            
                window.location.href = href;

        }, 1000);
        
        
    });
    
    
    
    // Download CSV Interactions 
    $('a[data-element="download-csv"]').on('click', function(e) {
       
        
        e.preventDefault();
        var txt = this.getAttribute("data-val");
        console.log(txt);
        
        
        
        window.dataLayer.push({'event':'download-links',
                               'linkText': txt
                              });  
        
        
    });
    
    
    
    
    
    
    

});



