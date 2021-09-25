import axios from "axios"
import { useEffect, useState } from "react"

export const useQuery = ({ query, variables, consumeData, ignore }) => {
   const [loading, setLoading] = useState(false)

   useEffect(() => {
      if (!ignore) {
         let cancelRequest

         setLoading(true)

         axios({
            url: '/graphql',
            method: 'post',
            data: { query, variables },
            cancelToken: new axios.CancelToken(cancel => cancelRequest = cancel)
         }).then(response => {
            setLoading(false)
            consumeData(response.data.data)
         }).catch(error => {
            if (axios.isCancel(error)) {
               return
            }
         })

         return () => {
            cancelRequest()
         }
      }
   }, [query, variables, consumeData, ignore])

   return loading
}
